import subprocess, shlex
import psutil
import copy
import sys
from typing import Union, Optional
from queue import Queue, Empty
from threading import Thread
import logging
import time

from Board import Move, Sign, GameRules
from utils import get_time, get_value
from exceptions import Timeouted, Crashed, TooMuchMemory, MadeIllegalMove, Interrupted


class Player:
    def __init__(self, config: dict):
        self._sign = Sign.EMPTY
        self._command = get_value(config, 'command')
        self._name = None
        self._timeout_turn = get_value(config, 'timeout_turn', 30.0)
        self._timeout_match = get_value(config, 'timeout_match', 180.0)
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
            logging.info('closing queue')

        self._queue = Queue()
        queue_thread = Thread(target=enqueue_output, args=(self._process.stdout, self._queue))
        queue_thread.daemon = True  # thread dies with the program
        queue_thread.start()

        self._pp = psutil.Process(self._process.pid)
        logging.info('successfully created process ' + self._command)
        self._suspend()

        self._is_engine_running = True
        self._received_messages = []
        self._sent_messages = []
        self._evaluation = {'memory': '?', 'depth': '?', 'score': '?', 'nodes': '?', 'speed': '?', 'time': '?', 'pv': '?'}
        self._is_now_on_move = False
        self._start_time = time.time()
        self._name = get_value(config, 'name', self._parse_name())  # engine name can be obtained only after the process has started, obviously...
        time.sleep(1.0)  # sleep so that all processes are not launched exactly at the same time (might mess up with logfiles, etc.)

    def _parse_name(self) -> str:
        self._resume()
        self._send('ABOUT')
        answer = self._get_response(self._time_left)
        fields = answer.split(',')
        informations = {}
        for field in fields:
            tmp = field.strip().split('=')
            informations[tmp[0]] = tmp[1].strip('"')

        result = ''
        if 'name' in informations:
            result += informations['name']
            if 'version' in informations:
                result += ' ' + informations['version']
        self._suspend()
        return result

    def _parse_evaluation(self, text: str) -> dict:
        assert text.startswith('MESSAGE ')
        result = {'memory': self.get_memory(), 'depth': '?', 'score': '?', 'nodes': '?', 'speed': '?', 'time': '?', 'pv': '?'}
        text.replace(', ', ' ')
        text.replace(' | ', ' ')
        text.replace('=', ' ')
        text.replace(':', ' ')
        text.replace(',', ' ')
        words = text[8:].split(' ')

        def find_info(name: str, keywords: list) -> None:
            for keyword in keywords:
                if keyword in words:
                    idx = words.index(keyword)
                    if idx + 1 < len(words):
                        result[name] = words[idx + 1]
                        return
            result[name] = '?'

        # [Embryo, AG], [PentaZen]
        find_info('depth', ['depth', 'dep'])

        # [Embryo, AG], [Barbakan], [Carbon], [Katagomo], [Pentazen]
        find_info('score', ['ev', 'value', 'eval', 'Winrate', 'sc'])

        # [Embryo, AG], [Barbakan], [Katagomo], [Pentazen]
        find_info('nodes', ['n', 'called', 'Visits', 'nd'])

        # [Embryo], [AG], [Carbon], [Pentazen]
        find_info('speed', ['n/s', 'n/ms', 'speed', 'sp'])

        # [Embryo, AG], [Katagomo]
        find_info('time', ['tm', 'Time'])

        # [Embryo, AG], [Katagomo]
        find_info('pv', ['pv', 'PV'])

        return result

    def _get_last_sent_command(self) -> str:
        if len(self._sent_messages) == 0:
            return ''
        else:
            return self._sent_messages[-1]

    @staticmethod
    def _parse_move_from_string(msg: str, sign: Sign) -> Move:
        assert sign == Sign.BLACK or sign == Sign.WHITE
        tmp = msg.split(',')
        assert len(tmp) == 2
        return Move(int(tmp[1]), int(tmp[0]), sign)

    @staticmethod
    def _is_message(msg: str) -> bool:
        return msg.startswith('MESSAGE') or msg.startswith('ERROR') or msg.startswith('UNKNOWN')

    def _send(self, msg: str) -> None:
        self._sent_messages.append(msg)
        logging.info('writing \'' + msg + '\' to engine \'' + self.get_name() + '\'')

        if msg[-1] != '\n':
            msg += '\n'
        try:
            self._process.stdin.write(msg.encode())
            self._process.stdin.flush()
        except Exception as e:
            logging.error(str(e))

    def _receive(self, timeout: float) -> Optional[str]:
        result = ''
        start = get_time()

        def time_used() -> float:
            return get_time() - start

        while self._is_engine_running and time_used() < timeout:
            try:
                buf = self._queue.get_nowait()
            except Empty:
                time.sleep(0.1)
            else:
                result += buf.decode('utf-8')

            if self.get_memory() > self._max_memory:
                raise TooMuchMemory(self.get_sign(), self.get_memory(), self._max_memory)

            if result.endswith('\n'):
                result = result.strip('\n')  # remove new line character at the end
                self._received_messages.append(result)
                logging.info('received \'' + result + '\' from engine \'' + self.get_name() + '\'')
                return result

        if self.is_alive():  # if process is alive and we got here it means timeout
            raise Timeouted(self.get_sign(), time_used(), timeout)
        elif self.is_on_move():  # if the process is dead but 'on move' it means crash
            raise Crashed(self.get_sign(), result, self._get_last_sent_command())
        else:  # if the process is neither alive nor 'on move' it means interruption
            raise Interrupted(self.get_sign())

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

    def _get_response(self, timeout: float) -> str:
        while True:
            answer = self._receive(timeout)
            if self._is_message(answer):
                if answer.startswith('MESSAGE'):
                    self._evaluation = self._parse_evaluation(answer)
            else:
                return answer

    def _timer_start(self) -> None:
        self._is_now_on_move = True
        self._start_time = time.time()

    def _timer_stop(self) -> None:
        self._is_now_on_move = False
        self._time_left -= (get_time() - self._start_time)

    def get_name(self) -> str:
        if self._name is None or self._name == '':
            return self._command
        else:
            return self._name

    def get_sign(self) -> Sign:
        return self._sign

    def set_sign(self, sign: Sign) -> None:
        self._sign = sign

    def get_memory(self) -> float:
        """

        :return: memory used by the process in MB
        """
        result = 0
        try:
            ds = list(self._pp.children(recursive=True))
            ds = ds + [self._pp]
            for d in ds:
                try:
                    result += d.memory_full_info()[7]
                except Exception as e:
                    logging.error(str(e))
        except Exception as e:
            pass
        return result / 1048576.0

    def get_time_left(self) -> float:
        if self._is_now_on_move:
            return self._time_left - (get_time() - self._start_time)
        else:
            return self._time_left

    def get_evaluation(self) -> dict:
        self._evaluation['memory'] = self.get_memory()
        return self._evaluation

    def set_time_left(self, time_left: float) -> None:
        """
        Used to resume a game with given amount of used time.
        :param time_left:
        :return:
        """
        self._time_left = time_left

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

        answer = self._get_response(self._tolerance + min(self._time_left, self._timeout_turn))
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
        answer = self._get_response(self._tolerance + min(self._time_left, self._timeout_turn))
        self._is_now_on_move = False

        self._suspend()
        self._timer_stop()
        return self._parse_move_from_string(answer, self._sign)

    def swap2board(self, list_of_moves) -> Union[str, list, Move]:
        """
        This method implements swap2 opening phase.
        If list of moves is empty, the engine will be asked to place first three stones.
        If list of moves has three elements, the engine will be asked to either swap, place 4th move, or two balancing moves.
        If list of moves has five elements, the engine will be asked to either swap or place 6th move.
        The engine does not have to obey the timeout_turn limit, only time_left.

        :param list_of_moves: list of moves that were already played
        :return: either string 'SWAP' or list of moves proposed by the engine
        """
        self._timer_start()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        if len(list_of_moves) == 0:
            self._send('SWAP2BOARD')
            self._send('DONE')
            answer = self._get_response(self._tolerance + self._time_left)
            self._suspend()
            self._timer_stop()

            tmp = answer.split(' ')
            assert len(tmp) == 3
            result = [self._parse_move_from_string(tmp[0], Sign.BLACK),
                      self._parse_move_from_string(tmp[1], Sign.WHITE),
                      self._parse_move_from_string(tmp[2], Sign.BLACK)]
            return result
        elif len(list_of_moves) == 3:
            self._send('SWAP2BOARD')
            for m in list_of_moves:
                self._send(str(m.col) + ',' + str(m.row))
            self._send('DONE')
            answer = self._get_response(self._tolerance + self._time_left)
            self._suspend()
            self._timer_stop()

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                if len(tmp) == 1:
                    result = [self._parse_move_from_string(tmp[0], Sign.WHITE)]
                    return result[0]
                elif len(tmp) == 2:
                    result = [self._parse_move_from_string(tmp[0], Sign.WHITE),
                              self._parse_move_from_string(tmp[1], Sign.BLACK)]
                    return result
                else:
                    raise MadeIllegalMove(self.get_sign(), answer)
        elif len(list_of_moves) == 5:
            self._send('SWAP2BOARD')
            for m in list_of_moves:
                self._send(str(m.col) + ',' + str(m.row))
            self._send('DONE')
            answer = self._get_response(self._tolerance + self._time_left)
            self._suspend()
            self._timer_stop()

            if answer == 'SWAP':
                return 'SWAP'
            else:
                tmp = answer.split(' ')
                assert len(tmp) == 1
                return self._parse_move_from_string(tmp[0], Sign.WHITE)
        else:
            raise MadeIllegalMove(self.get_sign(), 'incorrect number of moves')

    def turn(self, last_move: Move) -> Move:
        """
        :param last_move:
        :return:
        """
        self._timer_start()
        self._resume()
        self.info('time_left ' + str(int(1000 * self._time_left)))
        self._send('TURN ' + str(last_move.col) + ',' + str(last_move.row))
        answer = self._get_response(self._tolerance + min(self._time_left, self._timeout_turn))
        self._suspend()

        self._timer_stop()
        return self._parse_move_from_string(answer, self._sign)

    def end(self) -> None:
        self._resume()
        self._is_now_on_move = False
        self._send('END')
        time.sleep(self._tolerance)
        try:
            logging.info('player \'' + self.get_name() + '\' did not stop on time, killing process')
            if self.is_alive():
                for pp in self._pp.children(recursive=True):
                    pp.kill()
                self._pp.kill()
        except Exception as e:
            logging.error(str(e))
        self._is_engine_running = False

    def is_alive(self) -> bool:
        try:
            return self._process.poll() is None
        except Exception as e:
            logging.error(str(e))
            return False
