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

from local_launcher.Game import Move, Sign


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
        logging.info('successfully created process')

    def _parse_move_from_string(self, msg: str) -> Move:
        tmp = msg.split(',')
        assert len(tmp) == 2
        return Move(int(tmp[1]), int(tmp[0]), self._sign)

    def get_sign(self) -> Sign:
        return self._sign

    def send(self, msg: str) -> None:
        # print '===>', msg
        # sys.stdout.flush()
        logging.info('writing \'' + msg + '\' to engine')
        if msg[-1] != '\n':
            msg += '\n'
        self._process.stdin.write(msg.encode())
        self._process.stdin.flush()

    def receive(self) -> Optional[str]:
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
                return result[:-1]  # remove new line character at the end
        return None

    def update_time_left(self, tl: float) -> None:
        self._time_left = tl

    def suspend(self) -> None:
        try:
            self._pp.suspend()
        except Exception as e:
            logging.error(str(e))

    def resume(self) -> None:
        try:
            self._pp.resume()
        except Exception as e:
            logging.error(str(e))

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

    def stop_process(self) -> None:
        time.sleep(self._tolerance)
        if self._process.poll() is None:
            # self.process.kill()
            for pp in self._pp.children(recursive=True):
                pp.kill()
            self._pp.kill()
