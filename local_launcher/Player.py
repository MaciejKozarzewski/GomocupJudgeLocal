import subprocess, shlex
import psutil
import copy
import sys
from typing import Union, Optional
from utility import *
from queue import Queue, Empty
from threading import Thread
import logging
import time

from local_launcher.Game import Move, Sign, GameRules
from local_launcher.utils import get_time, get_value


class Player:
    def __init__(self, config: dict):
        self._sign = Sign.EMPTY
        self._command = get_value(config, 'command')
        self._name = get_value(config, 'name', self._command)
        self._timeout_turn = get_value(config, 'timeout_turn', 5.0)
        self._timeout_match = get_value(config, 'timeout_match', 12.0)
        self._time_left = self._timeout_match
        self._max_memory = get_value(config, 'max_memory', 350)
        self._folder = get_value(config, 'folder', '/.')
        self._allow_pondering = get_value(config, 'allow_pondering', False)
        self._tolerance = get_value(config, 'tolerance', 1.0)
        self._working_dir = get_value(config, 'working_dir', '/.')

        self._process = subprocess.Popen(shlex.split(self._command),
                                         shell=False,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         # bufsize=1,
                                         close_fds='posix' in sys.builtin_module_names,
                                         cwd=self._working_dir)

        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        self._queue = Queue()
        queue_thread = Thread(target=enqueue_output, args=(self._process.stdout, self._queue))
        queue_thread.daemon = True  # thread dies with the program
        queue_thread.start()

        self._pp = psutil.Process(self._process.pid)
        logging.info('successfully created process ' + self._command)
        self._suspend()

        self._message_log = []
        self._evaluation = ''
        self._is_now_on_move = False
        self._start_time = time.time()

    @staticmethod
    def _parse_move_from_string(msg: str, sign: Sign) -> Move:
        assert sign == Sign.CROSS or sign == Sign.CIRCLE
        tmp = msg.split(',')
        assert len(tmp) == 2
        return Move(int(tmp[1]), int(tmp[0]), sign)

    @staticmethod
    def _is_message(msg: str) -> bool:
        return msg.startswith('MESSAGE') or msg.startswith('ERROR') or msg.startswith('UNKNOWN')

    def _send(self, msg: str) -> None:
        # print '===>', msg
        # sys.stdout.flush()
        self._message_log.append('received : ' + msg)
        logging.info('writing \'' + msg + '\' to engine \'' + self._name + '\'')

        if msg[-1] != '\n':
            msg += '\n'
        self._process.stdin.write(msg.encode())
        self._process.stdin.flush()

    def _receive(self) -> Optional[str]:
        result = ''
        timeout_sec = self._tolerance + min(self._time_left, self._timeout_turn)
        start = get_time()
        while True:
            try:
                buf = self._queue.get_nowait()
            except Empty:
                if get_time() - start > timeout_sec:
                    break
                time.sleep(0.01)
            else:
                # print '<===', buf
                # sys.stdout.flush()
                result += buf.decode('utf-8')
            if result.endswith('\n'):
                self._message_log.append('answered : ' + result[:-1])
                logging.info('received \'' + result[:-1] + '\' from engine \'' + self._name + '\'')
                return result[:-1]  # remove new line character at the end
        return None

    def _suspend(self) -> None:
        if not self._allow_pondering:
            try:
                self._pp.suspend()
            except Exception as e:
                logging.error(str(e))

    def _resume(self) -> None:
        if not self._allow_pondering:
            try:
                self._pp.resume()
            except Exception as e:
                logging.error(str(e))

    def _get_response(self) -> str:
        while True:
            answer = self._receive()
            if answer is None:
                raise Exception('player has not responded correctly')
            elif self._is_message(answer):
                if answer.startswith('MESSAGE'):
                    self._evaluation = answer[8:]
            else:
                return answer

    def _timer_start(self) -> None:
        self._is_now_on_move = True
        self._start_time = time.time()

    def _timer_stop(self) -> None:
        self._is_now_on_move = False
        self._time_left -= (get_time() - self._start_time)

    def get_name(self) -> str:
        return self._name

    def get_sign(self) -> Sign:
        return self._sign

    def set_sign(self, sign: Sign) -> None:
        self._sign = sign

    def get_memory(self) -> int:
        result = 0
        try:
            ds = list(self._pp.children(recursive=True))
            ds = ds + [self._pp]
            for d in ds:
                try:
                    result += d.memory_info()[1]
                except Exception as e:
                    logging.error(str(e))
        except Exception as e:
            pass
        return result

    def get_message_log(self) -> list:
        return copy.deepcopy(self._message_log)

    def get_time_left(self) -> float:
        if self._is_now_on_move:
            return self._time_left - (get_time() - self._start_time)
        else:
            return self._time_left

    def get_evaluation(self) -> str:
        return self._evaluation

    def is_on_move(self) -> bool:
        return self._is_now_on_move

    def start(self, rows: int, columns: int, rules: GameRules) -> None:
        """
        Method used to initialize the engine with all necessary info about timeouts, rule, etc.
        :param rows:
        :param columns:
        :param rules:
        :return:
        """
        self._timer_start()
        self._resume()
        if rows == columns:
            self._send('START ' + str(rows))
        else:
            self._send('RECTSTART ' + str(columns) + ',' + str(rows))

        answer = self._get_response()
        if answer != 'OK':
            raise Exception('player has not responded \'OK\' to START command')

        self.info('rule ' + str(int(rules)))
        self.info("timeout_turn " + str(int(1000 * self._timeout_turn)))
        self.info("timeout_match " + str(int(1000 * self._timeout_match)))
        self.info("max_memory " + str(int(self._max_memory * 1024 * 1024)))
        self.info("game_type " + str(1))
        self.info("folder " + str(self._folder))
        self._suspend()
        self._timer_stop()

    def info(self, msg: str) -> None:
        """
        Method used to send info to the engine
        :param msg:
        :return:
        """
        self._send('INFO ' + msg)

    def board(self, list_of_moves: list) -> Move:
        """
        Method used to start the game with given opening. It calls either BEGIN if the opening is empty, or BOARD otherwise.

        :param list_of_moves: opening used for the game
        :return: first move made by the engine
        """
        self._timer_start()
        self._resume()

        self.info('time_left ' + str(int(1000 * self._time_left)))
        if len(list_of_moves) == 0:
            self._send('BEGIN')
        else:
            self._send('BOARD')
            for move in list_of_moves:
                assert move.sign != Sign.EMPTY
                if move.sign == self._sign:
                    self._send(str(move.col) + ',' + str(move.row) + ',1')
                else:
                    self._send(str(move.col) + ',' + str(move.row) + ',2')
            self._send('DONE')
        self._is_now_on_move = True
        answer = self._get_response()
        self._is_now_on_move = False

        self._suspend()
        self._timer_stop()
        return self._parse_move_from_string(answer, self._sign)

    def swap2board(self, list_of_moves) -> Union[str, list]:
        """
        This method implements swap2 opening phase.
        If list of moves is empty, the engine will be asked to place first three stones.
        If list of moves has three elements, the engine will be asked to either swap, place 4th move, or two balancing moves.
        If list of moves has five elements, the engine will be asked to either swap or place 6th move.

        :param list_of_moves: list of moves that were already played
        :return: either string 'SWAP' or list of moves proposed by the engine
        """
        self._timer_start()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        if len(list_of_moves) == 0:
            assert self._sign == Sign.CROSS
            self._send('SWAP2BOARD')
            self._send('DONE')
            answer = self._get_response()
            self._suspend()
            self._timer_stop()

            tmp = answer.split(' ')
            assert len(tmp) == 3
            result = [self._parse_move_from_string(tmp[0], Sign.CROSS),
                      self._parse_move_from_string(tmp[1], Sign.CIRCLE),
                      self._parse_move_from_string(tmp[2], Sign.CROSS)]
            return result
        elif len(list_of_moves) == 3:
            assert self._sign == Sign.CIRCLE
            self._send('SWAP2BOARD')
            for m in list_of_moves:
                self._send(str(m.col) + ',' + str(m.row))
            self._send('DONE')
            answer = self._get_response()
            self._suspend()
            self._timer_stop()

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                if len(tmp) == 1:
                    result = [self._parse_move_from_string(tmp[0], Sign.CIRCLE)]
                    return result
                elif len(tmp) == 2:
                    result = [self._parse_move_from_string(tmp[0], Sign.CIRCLE),
                              self._parse_move_from_string(tmp[1], Sign.CROSS)]
                    return result
                else:
                    raise Exception('incorrect answer for 3-stone opening')
        elif len(list_of_moves) == 5:
            assert self._sign == Sign.CROSS
            self._send('SWAP2BOARD')
            for m in list_of_moves:
                self._send(str(m.col) + ',' + str(m.row))
            self._send('DONE')
            answer = self._get_response()
            self._suspend()
            self._timer_stop()

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                assert len(tmp) == 1
                return [self._parse_move_from_string(tmp[0], Sign.CIRCLE)]
        else:
            raise Exception('too many stones placed in swap2')

    def turn(self, last_move: Move) -> Move:
        """
        :param last_move:
        :return:
        """
        self._timer_start()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        self._send('TURN ' + str(last_move.col) + ',' + str(last_move.row))
        answer = self._get_response()
        self._suspend()

        self._timer_stop()
        return self._parse_move_from_string(answer, self._sign)

    def end(self) -> None:
        self._resume()
        self._send('END')
        time.sleep(self._tolerance)
        if self._process.poll() is None:
            # self.process.kill()
            for pp in self._pp.children(recursive=True):
                pp.kill()
            self._pp.kill()
