from Board import Board, Move, Sign, GameOutcome
from Player import Player
import copy
from typing import Union
import numpy as np
import cv2


class Match:
    def __init__(self, board: Board, player1: Player, player2: Player, opening: str = ''):
        self._player1 = player1
        self._player2 = player2
        self._board = board
        self._move_log = []
        self._opening = copy.deepcopy(opening)
        self._frame = None
        self._prev_number_of_moves = -1

    def _get_black_player(self) -> Player:
        if self._player1.get_sign() == Sign.BLACK:
            return self._player1
        else:
            return self._player2

    def _get_white_player(self) -> Player:
        if self._player1.get_sign() == Sign.WHITE:
            return self._player1
        else:
            return self._player2

    def _get_player_to_move(self) -> Player:
        if self._board.get_sign_to_move() == Sign.BLACK:
            return self._get_black_player()
        else:
            return self._get_white_player()

    def _swap2(self) -> None:
        # first player chooses 3-stone opening
        player1_opening = self._player1.swap2board([])
        self._save_action(player1_opening)  # append opening for further PGN generation
        for m in player1_opening:
            self._board.make_move(m)

        player2_response = self._player2.swap2board(player1_opening)
        self._save_action(player2_response)

        if type(player2_response) == str:  # player2 decides to swap and therefore play as black
            assert str(player2_response) == 'SWAP'
            self._player1.set_sign(Sign.WHITE)
            self._player2.set_sign(Sign.BLACK)
            return
        else:
            assert type(player2_response) == list
            for m in player2_response:
                self._board.make_move(m)

            if len(player2_response) == 1:  # player2 decides to stay with white
                self._player1.set_sign(Sign.BLACK)
                self._player2.set_sign(Sign.WHITE)
                return
            elif len(player2_response) == 2:  # player2 decides to balance the position and let player1 choose the color
                player1_decision = self._player1.swap2board(player1_opening + player2_response)
                self._save_action(player1_decision)

                if type(player1_decision) == str:  # player1 decides to swap and therefore play as black
                    assert str(player1_decision) == 'SWAP'
                    self._player1.set_sign(Sign.BLACK)
                    self._player2.set_sign(Sign.WHITE)
                    return
                else:  # player1 decides to stay with white
                    assert type(player1_decision) == list and len(player1_decision) == 1
                    self._board.make_move(player1_decision[0])
                    self._player1.set_sign(Sign.WHITE)
                    self._player2.set_sign(Sign.BLACK)
                    return
            else:
                raise Exception('too many balancing stones')

    def _save_action(self, action: Union[Move, list, str]) -> None:
        def encode_move(move: Move) -> str:
            return chr(97 + move.row) + str(move.col)

        if type(action) == str:
            self._move_log.append(action)
        elif type(action) == Move:
            self._move_log.append(encode_move(action))
        elif type(action) == list:
            tmp = ''
            for move in action:
                tmp += encode_move(move) + ','
            self._move_log.append(tmp[:-1])  # cutting last character ','
        else:
            raise Exception('incorrect type')

    def play_game(self) -> GameOutcome:
        self._player1.start(self._board.rows(), self._board.cols(), self._board.rules())
        self._player2.start(self._board.rows(), self._board.cols(), self._board.rules())
        self._move_log = []

        if self._opening == 'swap2':
            self._swap2()
        elif len(self._opening) > 0:
            self._player1.set_sign(Sign.BLACK)
            self._player2.set_sign(Sign.WHITE)
            moves = self._opening.split(' ')
            for move in moves:
                tmp = move.split(',')
                self._save_action(move)
                self._board.make_move(Move(int(tmp[0]), int(tmp[1]), self._board.get_sign_to_move()))
        '''now the opening is prepared'''

        first_move = self._get_player_to_move().board(self._board.get_played_moves())
        self._save_action(first_move)
        self._board.make_move(first_move)

        second_move = self._get_player_to_move().board(self._board.get_played_moves())
        self._save_action(second_move)
        self._board.make_move(second_move)

        '''now both players got board state and can make moves'''
        while self._board.get_outcome() == GameOutcome.NO_OUTCOME:
            move = self._get_player_to_move().turn(self._board.get_last_move())
            self._save_action(move)
            self._board.make_move(move)

        self.cleanup()
        return self._board.get_outcome()

    def cleanup(self) -> None:
        self._player1.end()
        self._player2.end()

    def generate_pgn(self) -> str:
        result = '[White \"' + self._get_white_player().get_name() + '\"]\n'
        result += '[Black \"' + self._get_black_player().get_name() + '\"]\n'
        outcome = self._board.get_outcome()
        if outcome == GameOutcome.WHITE_WIN:
            tmp = '1-0'
        elif outcome == GameOutcome.BLACK_WIN:
            tmp = '0-1'
        elif outcome == GameOutcome.DRAW:
            tmp = '1/2-1/2'
        else:
            return ''  # TODO maybe it's better to throw an exception instead of returning empty PGN?
        result += '[Result \"' + tmp + '\"]\n'
        result += '1. N/A \n'
        # FIXME saving game history below
        # for i in range(0, len(self._move_log), 2):
        #     result += str(1 + i // 2) + '. '
        #     if i < len(self._move_log):
        #         result += self._move_log[i]
        #     if i + 1 < len(self._move_log):
        #         result += ' ' + self._move_log[i + 1] + ' '
        #     else:
        #         result += ' ' + tmp + '\n'
        return result

    def draw(self, size: int = 15) -> None:
        if self._board.number_of_moves() == self._prev_number_of_moves:
            return  # do not redraw if no new moves were played
        else:
            self._prev_number_of_moves = self._board.number_of_moves()

        height = (1 + 6 + self._board.rows() + 1) * size
        width = (1 + self._board.cols() + 1) * size
        if self._frame is None:
            self._frame = np.zeros((height, width, 3), dtype=np.uint8)

        '''fill background'''
        cv2.rectangle(self._frame, (0, 0), (width, height), color=(192, 192, 192), thickness=-1)

        '''highlight side to move'''
        if self._player1.is_on_move():
            cv2.rectangle(self._frame, (0, int(0.5 * size)), (width, int((0.5 + 3) * size)), color=(0, 255, 255), thickness=2)
        if self._player2.is_on_move():
            cv2.rectangle(self._frame, (0, int((0.5 + 3) * size)), (width, int((0.5 + 3 + 3) * size)), color=(0, 255, 255), thickness=2)

        def summarize_player(player: Player, x: int, y: int) -> None:
            text1 = player.get_name() + ' : ' + str(round(player.get_time_left(), 1)) + 's'
            eval = player.get_evaluation()
            text2 = str(eval['memory'] // (1024 * 1024)) + 'MB'
            text_depth = 'depth = ' + eval['depth']
            text_score = 'score = ' + eval['score']
            text_nodes = 'nodes = ' + eval['nodes']
            text_speed = 'speed = ' + eval['speed']
            if player.get_sign() == Sign.BLACK:
                color = (0, 0, 0)
                thickness = -1
            elif player.get_sign() == Sign.WHITE:
                color = (255, 255, 255)
                thickness = -1
            else:
                color = (0, 0, 0)
                thickness = 1
            cv2.circle(self._frame, (int(0.5 * size + y), x - int(1.8 * size)), size * 4 // 10, color, thickness=thickness)
            cv2.putText(self._frame, text1, (y + size, x - int(1.5 * size)), cv2.QT_FONT_NORMAL, 0.8, color=(0, 0, 0), thickness=1)
            cv2.putText(self._frame, text2, (y, x), cv2.QT_FONT_NORMAL, 0.8, color=(0, 0, 0), thickness=1)

            cv2.putText(self._frame, text_depth, (y + 4 * size, x - size // 2), cv2.QT_FONT_NORMAL, 0.6, color=(0, 0, 0), thickness=1)
            cv2.putText(self._frame, text_score, (y + 10 * size, x - size // 2), cv2.QT_FONT_NORMAL, 0.6, color=(0, 0, 0), thickness=1)
            cv2.putText(self._frame, text_nodes, (y + 4 * size, x + size // 4), cv2.QT_FONT_NORMAL, 0.6, color=(0, 0, 0), thickness=1)
            cv2.putText(self._frame, text_speed, (y + 10 * size, x + size // 4), cv2.QT_FONT_NORMAL, 0.6, color=(0, 0, 0), thickness=1)

        '''print info about players'''
        summarize_player(self._player1, 3 * size, int(0.5 * size))
        summarize_player(self._player2, 6 * size, int(0.5 * size))

        '''draw board lines'''
        for i in range(self._board.rows() - 1):
            for j in range(self._board.cols() - 1):
                x0 = int((1 + 6 + i + 0.5) * size)
                y0 = int((1 + j + 0.5) * size)
                cv2.rectangle(self._frame, (y0, x0), (y0 + size, x0 + size), color=(0, 0, 0), thickness=1)

        '''highlight last move'''
        last_move = self._board.get_last_move()
        if last_move is not None:
            x0 = (1 + 6 + last_move.row) * size
            y0 = (1 + last_move.col) * size
            cv2.rectangle(self._frame, (y0, x0), (y0 + size, x0 + size), color=(0, 255, 255), thickness=1)

        '''draw all moves'''
        moves = self._board.get_played_moves()
        for move in moves:
            x0 = int((1 + 6 + move.row + 0.5) * size)
            y0 = int((1 + move.col + 0.5) * size)
            if move.sign == Sign.BLACK:
                cv2.circle(self._frame, (y0, x0), size * 4 // 10, (0, 0, 0), thickness=-1)
            else:
                cv2.circle(self._frame, (y0, x0), size * 4 // 10, (255, 255, 255), thickness=-1)

        tmp_text = str(self._board.number_of_moves()) + ' move'
        if self._board.number_of_moves() > 1:
            tmp_text += 's'
        cv2.putText(self._frame, tmp_text, (size, height - size // 2), cv2.QT_FONT_NORMAL, 0.8, color=(0, 0, 0), thickness=1)

    def get_frame(self) -> np.ndarray:
        return self._frame

    def text_summary(self) -> str:
        pass
