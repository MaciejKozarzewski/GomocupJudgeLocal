from game_rules import Sign


class Timeouted(Exception):
    def __init__(self, player_name: str, player_sign: Sign, time_used: float, timeout: float):
        self.name = player_name
        self.sign = player_sign
        self.time_used = time_used
        self.timeout = timeout
        super().__init__('timeout = used ' + str(self.time_used) + '/' + str(self.timeout) + ' seconds')


class Crashed(Exception):
    def __init__(self, player_name: str, player_sign: Sign, answer: str, request: str):
        self.name = player_name
        self.sign = player_sign
        self.answer = answer
        self.request = request
        super().__init__('crash = responded with \'' + answer + '\' to \'' + request + '\'')


class MadeFoulMove(Exception):
    def __init__(self, player_name: str, player_sign: Sign):
        self.name = player_name
        self.sign = player_sign
        super().__init__('foul')


class MadeIllegalMove(Exception):
    def __init__(self, player_name: str, player_sign: Sign):
        self.name = player_name
        self.sign = player_sign
        super().__init__('illegal')


class TooMuchMemory(Exception):
    def __init__(self, player_name: str, player_sign: Sign, used_memory: float, max_memory: float):
        self.name = player_name
        self.sign = player_sign
        self.used_memory = used_memory
        self.max_memory = max_memory
        super().__init__('memory = used ' + str(self.used_memory) + '/' + str(self.max_memory) + ' MB')


class Interrupted(Exception):
    def __init__(self, player_name: str, player_sign: Sign):
        self.name = player_name
        self.sign = player_sign
        super().__init__('interrupted')
