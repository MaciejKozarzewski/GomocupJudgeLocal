import numpy as np
import copy
from enum import IntEnum, Enum
from local_launcher.Game import Sign

'''
All methods here returns true if stone at board[row][col] is a part of a winning line, false otherwise.
'''


class GameRules(Enum):
    FREESTYLE = 0
    STANDARD = 1
    RENJU = 2
    CARO = 4

    def __str__(self) -> str:
        if self.value == GameRules.FREESTYLE:
            return 'FREESTYLE'
        elif self.value == GameRules.FREESTYLE:
            return 'STANDARD'
        elif self.value == GameRules.FREESTYLE:
            return 'RENJU'
        else:
            return 'CARO'


class Direction(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1
    DIAGONAL = 2
    ANTIDIAGONAL = 3


all_directions = [Direction.HORIZONTAL, Direction.VERTICAL, Direction.DIAGONAL, Direction.ANTIDIAGONAL]


class Line:
    def __init__(self, board: np.ndarray, row: int, col: int, direction: Direction):
        """
        Creates a line of stones on board around point (row, col) in specified direction.
        :param board:
        :param row:
        :param col:
        :param direction:
        """
        self._line = ''
        dir_row = [1, 0, 1, 1]
        dir_col = [0, 1, 1, -1]
        for i in range(-5, 6, 1):
            x = row + dir_row[direction] * i
            y = col + dir_col[direction] * i
            if 0 <= x < board.shape[0] and 0 <= y < board.shape[1]:  # check if position is valid
                self._line += str(Sign(board[x][y]))
            else:
                self._line += str(Sign.OUT_OF_BOARD)

        self._overlines = ['XXXXXX']
        self._fives = ['XXXXX']
        self._fours = ['XXXX_', 'XXX_X', 'XX_XX', 'X_XXX', '_XXXX']
        self._inline_double_fours = ['XXX_X_XXX', 'XX_XX_XX', 'X_XXX_X']
        self._threes = []  # TODO for renju rule
        self._inline_double_threes = []  # TODO for renju rule
        self._blocked_fives = ['OXXXXO']

    @staticmethod
    def _invert_line(line: str) -> str:
        result = ''
        for i in range(len(line)):
            if line[i] == 'X':
                result += 'O'
            elif line[i] == 'O':
                result += 'X'
            else:
                result += line[i]
        return result

    def _has_pattern(self, sign: Sign, list_of_patterns: list) -> bool:
        if sign == Sign.CROSS or sign == Sign.CIRCLE:
            '''patterns are defined for cross, so to handle circles we have to invert signs'''
            tmp_line = self._line if sign == Sign.CIRCLE else self._invert_line(self._line)
            return any((pattern in tmp_line) for pattern in list_of_patterns)
        else:
            return False

    def is_overline(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._overlines)

    def is_five(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._fives)

    def is_four(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._fours)

    def is_double_four(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._inline_double_fours)

    def is_three(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._threes)

    def is_double_three(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._inline_double_threes)

    def is_blocked_five(self, sign: Sign) -> bool:
        return self._has_pattern(sign, self._blocked_fives)


def check_freestyle(board: np.ndarray, row: int, col: int) -> bool:
    assert 0 <= row < board.shape[0] and 0 <= col < board.shape[1]
    sign = Sign(board[row][col])
    for direction in all_directions:
        if Line(board, row, col, direction).is_five(sign):
            return True
    return False


def check_standard(board: np.ndarray, row: int, col: int) -> bool:
    assert 0 <= row < board.shape[0] and 0 <= col < board.shape[1]
    sign = Sign(board[row][col])
    is_five = False
    is_overline = False
    for direction in all_directions:
        line = Line(board, row, col, direction)
        if line.is_five(sign):
            is_five = True
        if line.is_overline(sign):
            is_overline = True
    return is_five and not is_overline


def check_renju(board: np.ndarray, row: int, col: int) -> bool:
    """
    Adapted from Piskvork
    (C) 2012-2015 Tianyi Hao
    (C) 2016 Petr Lastovicka
    (C) 2017 Kai Sun
    This program is free software: you can redistribute it and/or modify it under the terms of
    the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
    without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this program.
    If not, see <http://www.gnu.org/licenses/.
    """
    if board[row][col] == Sign.CIRCLE:
        return check_standard(board, row, col)

    # currently only deal with square board
    global l1, l2, l3, l4, X, Y
    X, Y = row, col
    if len(board) != len(board[0]):
        return False
    N = len(board)
    x1 = [[0 for i in range(N + 4)] for j in range(N)]
    x2 = [[0 for i in range(N + 4)] for j in range(N)]
    x3 = [[0 for i in range(N + 4)] for j in range(2 * N - 1)]
    x4 = [[0 for i in range(N + 4)] for j in range(2 * N - 1)]
    COMB = lambda x: (0x100 | x)
    COMC = lambda x, y: (0x10000 | ((x) << 8) | y)

    class line(object):
        def setline(self, a, p):
            a[2 + p] = 1
            self.x = a[2:]
            self.p = p

        def A6(self):
            x = self.x
            p = self.p
            for i in range(max(p - 5, 0), min(p, N - 6) + 1):
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] + x[i + 4] + x[i + 5] == 6:  # XXXXXX
                    return 1
            return 0

        def A5(self):
            x = self.x
            p = self.p
            for i in range(max(p - 4, 0), min(p, N - 5) + 1):
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] + x[i + 4] == 5 and x[i - 1] != 1 and x[i + 5] != 1:  # XXXXX
                    return 1
            return 0

        def B4(self):
            x = self.x
            p = self.p
            for i in range(max(p - 4, 0), min(p, N - 5) + 1):
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] + x[i + 4] == 4 and \
                        x[i - 1] != 1 and x[i + 5] != 1:
                    if x[i + 4] == 0:  # XXXX_
                        return 1
                    elif x[i + 3] == 0:  # XXX_X
                        if p == i + 4 and x[i + 5] == 0 and x[i + 6] == 1 and \
                                x[i + 7] == 1 and x[i + 8] == 1 and x[i + 9] != 1:  # XXX_X_XXX
                            return 2
                        return 1
                    elif x[i + 2] == 0:  # XX_XX
                        if (p == i + 4 or p == i + 3) and x[i + 5] == 0 and \
                                x[i + 6] == 1 and x[i + 7] == 1 and x[i + 8] != 1:  # XX_XX_XX
                            return 2
                        return 1
                    elif x[i + 1] == 0:  # X_XXX
                        if (x[i + 5] == 0 and x[i + 6] == 1 and x[i + 7] != 1) and \
                                (p == i + 4 or p == i + 3 or p == i + 2):  # X_XXX_X
                            return 2
                        return 1
                    else:  # _XXXX
                        return 1
            return 0

        def A3(self):
            x = self.x
            p = self.p
            for i in range(max(p - 3, 0), min(p, N - 4) + 1):
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] == 3 and x[i - 1] == 0 and x[i - 2] != 1:
                    if x[i + 3] == 0:  # XXX_
                        if x[i + 4] != 1:
                            if x[i - 2] == 0 and x[i - 3] != 1:  # __XXX_
                                if x[i + 4] == 0 and x[i + 5] != 1:  # __XXX___
                                    return COMC(i - 1, i + 3)
                                return COMB(i - 1)
                            if x[i + 4] == 0 and x[i + 5] != 1:  # _XXX__
                                return COMB(i + 3)
                    elif x[i + 2] == 0:  # XX_X
                        if x[i + 4] == 0 and x[i + 5] != 1:
                            return COMB(i + 2)
                    elif x[i + 1] == 0:  # X_XX
                        if x[i + 4] == 0 and x[i + 5] != 1:
                            return COMB(i + 1)
            return 0

    def pad(x, c, l):
        for i in range(c):
            x[i][0] = x[i][1] = 20
            for j in range(l, N + 2):
                x[i][j + 2] = 20

    pad(x1, N, N)
    pad(x2, N, N)
    pad(x3, 2 * N - 1, 0)
    pad(x4, 2 * N - 1, 0)
    for i in range(N):
        for j in range(N):
            x1[i][j + 2] = x2[j][i + 2] = x3[i + j][j + 2] = x4[N - 1 - j + i][N - 1 - j + 2] = 0 if board[i][
                                                                                                         j] == 0 else (
                1 if board[i][j] == 1 else -1)
    l1 = line()
    l2 = line()
    l3 = line()
    l4 = line()

    def A3(l, f):
        r = l.A3()
        return r and (not f(r & 0xff) or r >= 0x10000 and not f((r >> 8) & 0xff))

    def foulr(x, y, five):
        global l1, l2, l3, l4, X, Y
        result = 0
        if x1[x][y + 2] != -1:
            m1 = copy.deepcopy(l1)
            m2 = copy.deepcopy(l2)
            m3 = copy.deepcopy(l3)
            m4 = copy.deepcopy(l4)
            x0, y0 = X, Y
            X, Y = x, y
            sign = x1[x][y + 2]
            l1.setline(x1[x], y)
            l2.setline(x2[y], x)
            l3.setline(x3[x + y], y)
            l4.setline(x4[N - 1 - y + x], N - 1 - y)
            f1 = lambda r: foulr(X, r, 1)
            f2 = lambda r: foulr(r, Y, 1)
            f3 = lambda r: foulr(X + Y - r, r, 1)
            f4 = lambda r: foulr(N - 1 + X - Y - r, N - 1 - r, 1)
            if l1.A5() == 1 or l2.A5() == 1 or l3.A5() == 1 or l4.A5() == 1:
                result = five  # five in a row
            elif l1.B4() + l2.B4() + l3.B4() + l4.B4() >= 2:
                result = 2  # double-four
            elif A3(l1, f1) + A3(l2, f2) + A3(l3, f3) + A3(l4, f4) >= 2:
                result = 1  # double-three
            elif l1.A6() == 1 or l2.A6() == 1 or l3.A6() == 1 or l4.A6() == 1:
                result = 3  # overline
            x1[x][y + 2] = x2[y][x + 2] = x3[x + y][y + 2] = x4[N - 1 - y + x][N - 1 - y + 2] = sign
            l1 = m1
            l2 = m2
            l3 = m3
            l4 = m4
            X, Y = x0, y0
        return result

    return foulr(X, Y, 0) != 0


def check_caro(board: np.ndarray, row: int, col: int) -> bool:
    assert 0 <= row < board.shape[0] and 0 <= col < board.shape[1]
    sign = Sign(board[row][col])
    is_five = False
    is_overline = False
    for direction in all_directions:
        line = Line(board, row, col, direction)
        if line.is_five(sign) and not line.is_blocked_five(sign):
            is_five = True
        if line.is_overline(sign):
            is_overline = True
    return is_five and not is_overline
