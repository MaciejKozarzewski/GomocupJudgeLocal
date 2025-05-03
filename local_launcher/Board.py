from __future__ import annotations
import numpy as np
import copy
from enum import IntEnum
from typing import Optional
from utils import get_value
from game_rules import Sign, Move, GameRules, FoulType, is_winning, is_forbidden, get_foul_type
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
        self._forbidden_moves = []

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
        if self.is_inside(move.row, move.col) and self.get_sign_at(move.row, move.col) == Sign.EMPTY and \
                (move.sign == Sign.BLACK or move.sign == Sign.WHITE):

            if self._rules == GameRules.RENJU and move.sign == Sign.BLACK:
                ft = get_foul_type(np.copy(self._board), move)
                if ft is not None:
                    raise MadeFoulMove(move, ft)

            self._board[move.row][move.col] = int(move.sign)
            self._played_moves.append(copy.deepcopy(move))
        else:
            raise MadeIllegalMove(move.sign, move)

        self._forbidden_moves = []
        if self._rules == GameRules.RENJU:
            for r in range(self.rows()):
                for c in range(self.cols()):
                    if self._board[r][c] == 0:
                        if is_forbidden(np.copy(self._board), Move(r, c, Sign.BLACK)):
                            self._forbidden_moves.append(Move(r, c, Sign.BLACK))

    def is_inside(self, row: int, column: int) -> bool:
        return 0 <= row < self.rows() and 0 <= column < self.cols()

    def is_full(self) -> bool:
        result = 0
        for row in range(self.rows()):
            for col in range(self.cols()):
                result += int(self.get_sign_at(row, col) == Sign.EMPTY)
        return result == 0

    def get_outcome(self) -> GameOutcome:
        if self.number_of_moves() == 0:  # no outcome for empty board
            return GameOutcome.NO_OUTCOME

        last_move = self.get_last_move()

        outcome = is_winning(self._rules, np.copy(self._board), last_move)

        if outcome == 1:
            if last_move.sign == Sign.BLACK:
                return GameOutcome.BLACK_WIN
            else:
                return GameOutcome.WHITE_WIN
        elif outcome < 0:
            assert last_move.sign == Sign.BLACK, 'only black player can make foul move'
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

    def get_forbidden_moves(self) -> list:
        return self._forbidden_moves


# if __name__ == '__main__':
#     board = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 1, 2, 0],
#                       [0, 0, 0, 0, 0, 2, 0, 2, 2, 1, 0, 2, 1, 0, 0],
#                       [0, 0, 0, 0, 0, 1, 1, 1, 0, 2, 1, 2, 0, 0, 0],
#                       [0, 0, 0, 0, 0, 2, 0, 1, 0, 1, 2, 1, 0, 0, 2],
#                       [0, 0, 0, 0, 1, 0, 1, 2, 1, 2, 2, 2, 2, 1, 0],
#                       [0, 0, 0, 0, 0, 2, 0, 2, 1, 2, 2, 1, 1, 1, 1],
#                       [0, 0, 0, 0, 0, 1, 2, 1, 2, 1, 1, 0, 0, 2, 1],
#                       [0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 1, 2, 0],
#                       [0, 0, 0, 0, 0, 0, 1, 0, 2, 2, 2, 1, 2, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 2, 2, 2, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
#                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0]])
#
#     for i in range(15):
#         for j in range(15):
#             if board[i, j] == 0:
#                 if is_forbidden(np.copy(board), Move(i, j, Sign.BLACK)):
#                     print(i, j)
#
#     asdf = Board({'rules': 'renju',
#                   'rows': 15,
#                   'cols': 15})
#
#     asdf._board = board
#     print(asdf.to_string())
#     asdf.make_move(Move(3, 4, Sign.WHITE))
#     print(asdf.get_forbidden_moves())
#     pass
