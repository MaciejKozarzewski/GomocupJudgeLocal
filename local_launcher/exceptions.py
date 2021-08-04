from typing import Union
from game_rules import Sign, FoulType, Move


class Timeouted(Exception):
    def __init__(self, player_sign: Sign, time_used: float, timeout: float):
        self.sign = player_sign
        self.time_used = time_used
        self.timeout = timeout
        super().__init__('timeout = used ' + str(self.time_used) + '/' + str(self.timeout) + ' seconds')


class Crashed(Exception):
    def __init__(self, player_sign: Sign, answer: str, request: str):
        self.sign = player_sign
        self.answer = answer
        self.request = request
        super().__init__('crash = responded with \'' + answer + '\' to \'' + request + '\'')


class MadeFoulMove(Exception):
    def __init__(self, player_sign: Sign, move: Move, foul_type: FoulType):
        self.sign = player_sign
        self.move = move
        self.foul_type = foul_type
        super().__init__('foul = ' + str(foul_type) + ' at (' + str(move) + '0')


class MadeIllegalMove(Exception):
    def __init__(self, player_sign: Sign, move: Union[str, Move]):
        self.sign = player_sign
        self.move = move
        if type(move) == Move:
            super().__init__('illegal = move at (' + str(move) + ')')
        else:
            super().__init__('illegal = move action \'' + str(move) + '\'')


class TooMuchMemory(Exception):
    def __init__(self, player_sign: Sign, used_memory: float, max_memory: float):
        self.sign = player_sign
        self.used_memory = used_memory
        self.max_memory = max_memory
        super().__init__('memory = used ' + str(self.used_memory) + '/' + str(self.max_memory) + ' MB')


class Interrupted(Exception):
    def __init__(self, player_sign: Sign):
        self.sign = player_sign
        super().__init__('interrupted')
