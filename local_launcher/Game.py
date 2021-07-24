import numpy as np
import copy
from enum import Enum
from typing import Optional
from threading import Lock
from local_launcher.utils import get_value
from local_launcher.game_rules import Sign, GameRules, check_freestyle, check_standard, check_renju, check_caro, is_forbidden


class GameOutcome(Enum):
    NO_OUTCOME = 0
    DRAW = 1
    CROSS_WIN = 2
    CIRCLE_WIN = 3


class Move:
    def __init__(self, row: int, col: int, sign: Sign):
        self.row = row
        self.col = col
        self.sign = sign

    def __str__(self) -> str:
        return str(self.col) + ' ' + str(self.row)


class Game:
    def __init__(self, config: dict):
        self._game_lock = Lock()
        self._rules = GameRules.from_string(get_value(config, 'rules'))

        self._board = np.zeros((get_value(config, 'rows'), get_value(config, 'cols')), dtype=np.int32)
        self._played_moves = []

    def to_string(self) -> str:
        result = ''
        for row in range(self.rows()):
            for col in range(self.cols()):
                result += str(Sign(self._board[row][col])) + ' '
            result += '\n'
        return result

    def from_moves(self, list_of_moves: list) -> None:
        """
        Moves in the list must be in the same order they was played.
        :param list_of_moves:
        :return:
        """
        with self._game_lock:
            self._played_moves = []
            for move in list_of_moves:
                self.make_move(move)

    def get_sign_to_move(self) -> Sign:
        with self._game_lock:
            if len(self._played_moves) == 0:
                return Sign.CROSS
            else:
                if self._played_moves[-1].sign == Sign.CROSS:
                    return Sign.CIRCLE
                else:
                    return Sign.CROSS

    def is_square(self) -> bool:
        return self.rows() == self.cols()

    def rows(self) -> int:
        return self._board.shape[0]

    def cols(self) -> int:
        return self._board.shape[1]

    def rules(self) -> GameRules:
        return self._rules

    def get_sign_at(self, row: int, col: int) -> Sign:
        assert 0 <= row < self.rows() and 0 <= col < self.cols()
        with self._game_lock:
            return Sign(self._board[row][col])

    def number_of_moves(self) -> int:
        with self._game_lock:
            return len(self._played_moves)

    def get_played_moves(self) -> list:
        with self._game_lock:
            return copy.deepcopy(self._played_moves)

    def get_last_move(self) -> Optional[Move]:
        with self._game_lock:
            if len(self._played_moves) == 0:
                return None
            else:
                return copy.deepcopy(self._played_moves[-1])

    def make_move(self, move: Move) -> None:
        assert 0 <= move.row < self.rows() and 0 <= move.col < self.cols() and \
               (move.sign == Sign.CROSS or move.sign == Sign.CIRCLE) and \
               self.get_sign_at(move.row, move.col) == Sign.EMPTY
        with self._game_lock:
            self._board[move.row][move.col] = int(move.sign)
            self._played_moves.append(copy.deepcopy(move))

    def get_outcome(self) -> GameOutcome:
        if self.number_of_moves() == 0:  # no outcome for empty board
            return GameOutcome.NO_OUTCOME

        if self._is_move_forbidden(self.get_last_move()):  # if last move was forbidden, the other player wins
            if self.get_last_move().sign == Sign.CROSS:
                return GameOutcome.CIRCLE_WIN
            else:
                return GameOutcome.CROSS_WIN
        elif self._is_move_winning(self.get_last_move()):  # if last move was winning, this player wins
            if self.get_last_move().sign == Sign.CROSS:
                return GameOutcome.CROSS_WIN
            else:
                return GameOutcome.CIRCLE_WIN

        empty_spots = 0
        for row in range(self.rows()):
            for col in range(self.cols()):
                if self.get_sign_at(row, col) == Sign.EMPTY:
                    empty_spots += 1

        # no winner was found
        if self._rules == GameRules.FREESTYLE:
            if empty_spots == 0:  # for freestyle rule the game can be played until board is full
                return GameOutcome.DRAW
        else:  # for other rules it might not be possible to play until full board
            if empty_spots < 0.125 * self.rows() * self.cols():  # TODO maybe even lower threshold is necessary
                return GameOutcome.DRAW

        return GameOutcome.NO_OUTCOME

    def _is_move_winning(self, move: Move) -> bool:
        if self.get_sign_at(move.row, move.col) != Sign.EMPTY:
            if self._rules == GameRules.FREESTYLE:
                return check_freestyle(self._board, move.row, move.col)
            elif self._rules == GameRules.STANDARD:
                return check_standard(self._board, move.row, move.col)
            elif self._rules == GameRules.RENJU:
                return check_renju(self._board, move.row, move.col)
            else:
                return check_caro(self._board, move.row, move.col)
        else:
            return False

    def _is_move_forbidden(self, move: Move) -> bool:
        if self._rules == GameRules.RENJU:
            return is_forbidden(self._board, move.row, move.col)
        else:
            return False
