import numpy as np
import copy
from enum import Enum
from typing import Optional
from local_launcher.game_rules import Sign, GameRules, check_freestyle, check_standard, check_renju, check_caro, \
    is_forbidden


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
    def __init__(self, rows: int, columns: int, rules: GameRules):
        self._rules = rules

        self._board = np.zeros((rows, columns), dtype=np.int32)
        self._played_moves = []

    def to_string(self) -> str:
        result = ''
        for row in range(self.rows()):
            for col in range(self.cols()):
                result += str(Sign(self._board[row][col])) + ' '
            result += '\n'
        return result

    def from_string(self, board: str, sign_to_move: Sign) -> None:
        moves_cross = []
        moves_circle = []
        tmp = []
        current_line = []
        for c in board:
            if c == 'X':
                moves_cross.append(Move(len(tmp), len(current_line), Sign.CROSS))
                current_line.append(int(Sign.CROSS))
            elif c == 'O':
                moves_circle.append(Move(len(tmp), len(current_line), Sign.CIRCLE))
                current_line.append(int(Sign.CIRCLE))
            elif c == '_':
                current_line.append(int(Sign.EMPTY))
            elif c == '\n':
                tmp.append(copy.deepcopy(current_line))
                current_line = []
        self._board = np.array(tmp)
        if sign_to_move == Sign.CROSS:
            self._played_moves = moves_cross + moves_circle
        else:
            self._played_moves = moves_circle + moves_cross

    def from_moves(self, list_of_moves: list) -> None:
        for move in list_of_moves:
            self.make_move(move)

    def get_sign_to_move(self) -> Sign:
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
            return self._played_moves[-1]

    def make_move(self, move: Move) -> None:
        assert 0 <= move.row < self.rows() and 0 <= move.col < self.cols() and \
               (move.sign == Sign.CROSS or move.sign == Sign.CIRCLE) and \
               self.get_sign_at(move.row, move.col) == Sign.EMPTY
        self._board[move.row][move.col] = int(move.sign)
        self._played_moves.append(copy.deepcopy(move))

    def get_outcome(self) -> GameOutcome:
        empty_spots = 0
        for row in range(self.rows()):
            for col in range(self.cols()):
                if self.get_sign_at(row, col) == Sign.EMPTY:
                    empty_spots += 1
                else:
                    if self.is_move_winning(Move(row, col, self.get_sign_at(row, col))):
                        if self.get_sign_at(row, col) == Sign.CROSS:
                            print(row, col)
                            return GameOutcome.CROSS_WIN
                        if self.get_sign_at(row, col) == Sign.CIRCLE:
                            return GameOutcome.CIRCLE_WIN
        # no winner was found
        if self._rules == GameRules.FREESTYLE:
            if empty_spots == 0:
                return GameOutcome.DRAW
            else:
                return GameOutcome.NO_OUTCOME
        else:
            if empty_spots < 0.1 * self.rows() * self.cols():
                return GameOutcome.DRAW
            else:
                return GameOutcome.NO_OUTCOME

    def is_move_winning(self, move: Move) -> bool:
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


if __name__ == '__main__':
    txt = ' _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n' \
          ' _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n' \
          ' _ _ _ _ _ _ X _ _ _ _ _ _ _ _\n' \
          ' _ _ _ _ _ X O O O O O X _ _ _\n' \
          ' _ _ _ _ _ _ _ X O X _ _ _ _ _\n' \
          ' _ _ _ _ _ _ O X X O X _ _ _ _\n' \
          ' _ _ _ _ O X X X X O O X O _ _\n' \
          ' _ _ _ O X O _ X O X X X X O _\n' \
          ' X O X X X O X O X O O O X O _\n' \
          ' _ _ O O O X _ O X O X O O X _\n' \
          ' _ X O O O X O _ _ O X X X X O\n' \
          ' _ _ X _ _ O _ X O X O O X X _\n' \
          ' _ _ _ _ X _ X O X O _ _ _ O _\n' \
          ' _ _ _ _ _ _ X O _ _ _ O _ X _\n' \
          ' _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n'

    board = Game(15, 15, GameRules.CARO)
    board.from_string(txt, Sign.CROSS)
    print(board.to_string())
    print(board.get_sign_to_move())
    print(board.get_outcome())
