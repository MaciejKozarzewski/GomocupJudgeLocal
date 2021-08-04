from __future__ import annotations
import numpy as np
import copy
from enum import IntEnum
from typing import Optional
from utils import get_value
from game_rules import Sign, Move, GameRules, check_freestyle, check_standard, check_renju, check_caro, is_forbidden
from exceptions import MadeIllegalMove, MadeFoulMove


class GameOutcome(IntEnum):
    NO_OUTCOME = 0
    DRAW = 1
    BLACK_WIN = 2
    WHITE_WIN = 3

    def __str__(self) -> str:
        if self.value == GameOutcome.NO_OUTCOME:
            return 'NO_OUTCOME'
        elif self.value == GameOutcome.DRAW:
            return 'DRAW'
        elif self.value == GameOutcome.BLACK_WIN:
            return 'BLACK_WIN'
        else:
            return 'WHITE_WIN'

    @staticmethod
    def from_string(s: str) -> GameOutcome:
        if s.lower() == 'no_outcome':
            return GameOutcome.NO_OUTCOME
        elif s.lower() == 'draw':
            return GameOutcome.DRAW
        elif s.lower() == 'black_win':
            return GameOutcome.BLACK_WIN
        elif s.lower() == 'white_win':
            return GameOutcome.WHITE_WIN
        else:
            raise Exception('unknown game outcome \'' + s + '\'')


class Board:
    def __init__(self, config: dict):
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
        self._played_moves = []
        for move in list_of_moves:
            self.make_move(move)

    def get_sign_to_move(self) -> Sign:
        if len(self._played_moves) == 0:
            return Sign.BLACK
        else:
            if self._played_moves[-1].sign == Sign.BLACK:
                return Sign.WHITE
            else:
                return Sign.BLACK

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
        return Sign(self._board[row][col])

    def number_of_moves(self) -> int:
        return len(self._played_moves)

    def get_played_moves(self) -> list:
        return copy.deepcopy(self._played_moves)

    def get_last_move(self) -> Optional[Move]:
        if len(self._played_moves) == 0:
            return None
        else:
            return copy.deepcopy(self._played_moves[-1])

    def make_move(self, move: Move) -> None:
        if 0 <= move.row < self.rows() and 0 <= move.col < self.cols() and \
                (move.sign == Sign.BLACK or move.sign == Sign.WHITE) and \
                self.get_sign_at(move.row, move.col) == Sign.EMPTY:
            self._board[move.row][move.col] = int(move.sign)
            self._played_moves.append(copy.deepcopy(move))
        else:
            raise MadeIllegalMove(move.sign, move)

    def get_outcome(self) -> GameOutcome:
        if self.number_of_moves() == 0:  # no outcome for empty board
            return GameOutcome.NO_OUTCOME

        if self._is_move_forbidden(self.get_last_move()):  # if last move was forbidden, the other player wins
            if self.get_last_move().sign == Sign.BLACK:
                return GameOutcome.WHITE_WIN
            else:
                return GameOutcome.BLACK_WIN
        elif self._is_move_winning(self.get_last_move()):  # if last move was winning, this player wins
            if self.get_last_move().sign == Sign.BLACK:
                return GameOutcome.BLACK_WIN
            else:
                return GameOutcome.WHITE_WIN

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
