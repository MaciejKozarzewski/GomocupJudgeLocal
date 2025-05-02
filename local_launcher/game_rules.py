from __future__ import annotations

import numpy as np
import copy
from enum import IntEnum, Enum


class Sign(IntEnum):
    EMPTY = 0
    BLACK = 1
    WHITE = 2
    OUT_OF_BOARD = 3

    def __str__(self) -> str:
        if self.value == Sign.EMPTY:
            return '_'
        elif self.value == Sign.BLACK:
            return 'X'
        elif self.value == Sign.WHITE:
            return 'O'
        else:
            return '|'


class Move:
    def __init__(self, row: int, col: int, sign: Sign):
        self.row = row
        self.col = col
        self.sign = sign

    def __str__(self) -> str:
        return str(self.col) + ' ' + str(self.row)

    def save(self) -> str:
        """
        This method encodes move in the following format [X - black / O - white][letter - row][number - column].
        For example Xd4 means Black stone in row 3 (indexing from 0) and column 4 (also indexing from 0)
        :return:
        """
        return str(self.sign) + chr(97 + self.row) + str(self.col)

    @staticmethod
    def load(txt: str) -> Move:
        """
        This method decodes string created by the encode() method back into Move object.
        :param txt:
        :return:
        """
        assert (txt[0] == 'X' or txt[0] == 'O') and txt[1].isalpha() and txt[2:].isnumeric()
        if txt[0] == 'X':
            return Move(ord(txt[1]) - 97, int(txt[2:]), Sign.BLACK)
        else:
            return Move(ord(txt[1]) - 97, int(txt[2:]), Sign.WHITE)


class GameRules(IntEnum):
    FREESTYLE = 0
    STANDARD = 1
    RENJU = 4
    CARO5 = 8
    CARO6 = 9

    def __str__(self) -> str:
        if self.value == GameRules.FREESTYLE:
            return 'FREESTYLE'
        elif self.value == GameRules.STANDARD:
            return 'STANDARD'
        elif self.value == GameRules.RENJU:
            return 'RENJU'
        elif self.value == GameRules.CARO5:
            return 'CARO5'
        elif self.value == GameRules.CARO6:
            return 'CARO6'
        else:
            return 'UNKNOWN'

    @staticmethod
    def from_string(s: str) -> GameRules:
        if s.upper() == str(GameRules.FREESTYLE):
            return GameRules.FREESTYLE
        elif s.upper() == str(GameRules.STANDARD):
            return GameRules.STANDARD
        elif s.upper() == str(GameRules.RENJU):
            return GameRules.RENJU
        elif s.upper() == str(GameRules.CARO5):
            return GameRules.CARO5
        elif s.upper() == str(GameRules.CARO6):
            return GameRules.CARO6
        else:
            raise Exception('unknown rules \'' + s + '\'')


def is_forbidden(board: np.ndarray, move: Move) -> bool:
    # currently only deal with square board
    global l1, l2, l3, l4, X, Y
    X, Y = move.row, move.col
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
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] + x[i + 4] + x[i + 5] == 6:
                    return 1
            return 0

        def A5(self):
            x = self.x
            p = self.p
            for i in range(max(p - 4, 0), min(p, N - 5) + 1):
                if x[i] + x[i + 1] + x[i + 2] + x[i + 3] + x[i + 4] == 5 and \
                        x[i - 1] != 1 and x[i + 5] != 1:  # XXXXX
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


def is_winning(rule: GameRules, board: np.ndarray, move: Move) -> int:
    assert board.shape[0] == board.shape[1]
    board_size = board.shape[0]
    x, y = move.row, move.col

    if rule == GameRules.RENJU and move.sign == Sign.BLACK and is_forbidden(board, move):
        return -1

    nx = [0, 1, -1, 1]
    ny = [1, 0, 1, 1]
    for d in range(4):
        c = 1
        blocked = 0
        _x, _y = x, y
        for i in range(1, 6):
            _x += nx[d]
            _y += ny[d]
            if _x < 0 or _x >= board_size:
                break
            if _y < 0 or _y >= board_size:
                break
            if board[_x][_y] != board[x][y]:
                if board[_x][_y] != 0:
                    blocked += 1
                break
            c += 1
        _x, _y = x, y
        for i in range(1, 6):
            _x -= nx[d]
            _y -= ny[d]
            if _x < 0 or _x >= board_size:
                break
            if _y < 0 or _y >= board_size:
                break
            if board[_x][_y] != board[x][y]:
                if board[_x][_y] != 0:
                    blocked += 1
                break
            c += 1

        if (rule == GameRules.FREESTYLE or rule == GameRules.RENJU) and c >= 5:
            return 1
        if rule == GameRules.STANDARD and c == 5:
            return 1
        if rule == GameRules.CARO5 and c == 5 and blocked < 2:
            return 1
        if rule == GameRules.CARO6 and (c > 5 or (c == 5 and blocked < 2)):
            return 1
    return 0
