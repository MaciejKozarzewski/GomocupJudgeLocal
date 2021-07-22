import subprocess, shlex
import psutil
import copy
import time
import sys
from typing import Union, Optional
from utility import *
from queue import Queue, Empty
from threading import Thread
import logging

from local_launcher.Game import Move, Sign, GameRules


def get_time() -> float:
    return time.time()


class Player:
    def __init__(self,
                 sign: Sign,
                 command: str,
                 name: str = None,
                 timeout_turn: float = 5.0,  # in seconds
                 timeout_match: float = 120.0,  # in seconds
                 max_memory: int = 350 * 1024 * 1024,  # in bytes
                 folder: str = './',
                 working_dir: str = './',
                 allow_pondering: bool = False,
                 tolerance: float = 1.0):

        self._sign = sign
        if name is None:
            self._name = command
        else:
            self._name = name
        self._timeout_turn = timeout_turn
        self._timeout_match = timeout_match
        self._time_left = timeout_match
        self._max_memory = max_memory
        self._folder = folder
        self._allow_pondering = allow_pondering
        self._tolerance = tolerance

        self._process = subprocess.Popen(shlex.split(command),
                                         shell=False,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         # bufsize=1,
                                         close_fds='posix' in sys.builtin_module_names,
                                         cwd=working_dir)

        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        self._queue = Queue()
        queue_thread = Thread(target=enqueue_output, args=(self._process.stdout, self._queue))
        queue_thread.daemon = True  # thread dies with the program
        queue_thread.start()

        self._pp = psutil.Process(self._process.pid)
        logging.info('successfully created process ' + command)
        self._suspend()

        self._message_log = []

    @staticmethod
    def _parse_move_from_string(msg: str, sign: Sign) -> Move:
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
        start = time.time()
        while True:
            try:
                buf = self._queue.get_nowait()
            except Empty:
                if time.time() - start > timeout_sec:
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
            elif not self._is_message(answer):
                return answer

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
            logging.error(str(e))
        return result

    def start(self, rows: int, columns: int, rules: GameRules) -> None:
        """
        Method used to initialize the engine with all necessary info about timeouts, rule, etc.
        :param rows:
        :param columns:
        :param rules:
        :return:
        """
        start_time = get_time()
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
        self.info("max_memory " + str(self._max_memory))
        self.info("game_type " + str(1))
        self.info("folder " + str(self._folder))
        self._suspend()
        self._time_left -= (get_time() - start_time)

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
        start_time = get_time()
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
        answer = self._get_response()

        self._suspend()
        self._time_left -= (get_time() - start_time)
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
        start_time = get_time()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        if len(list_of_moves) == 0:
            assert self._sign == Sign.CROSS
            self._send('SWAP2BOARD')
            self._send('DONE')
            answer = self._get_response()
            self._suspend()
            self._time_left -= (get_time() - start_time)

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
            self._time_left -= (get_time() - start_time)

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                if len(tmp) == 1:
                    result = [self._parse_move_from_string(tmp[0], Sign.CROSS)]
                    return result
                elif len(tmp) == 2:
                    result = [self._parse_move_from_string(tmp[0], Sign.CROSS),
                              self._parse_move_from_string(tmp[1], Sign.CIRCLE)]
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
            self._time_left -= (get_time() - start_time)

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                assert len(tmp) == 1
                return [self._parse_move_from_string(tmp[0], Sign.CROSS)]
        else:
            raise Exception('too many stones placed in swap2')

    def turn(self, last_move: Move) -> Move:
        """
        :param last_move:
        :return:
        """
        start_time = get_time()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        self._send('TURN ' + str(last_move.col) + ',' + str(last_move.row))
        answer = self._get_response()
        self._suspend()
        self._time_left -= (get_time() - start_time)

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
