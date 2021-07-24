from local_launcher.Game import Game, Move, Sign, GameOutcome
from local_launcher.Player import Player
import copy
import numpy as np
import cv2


class Match:
    def __init__(self, game: Game, cross_player: Player, circle_player: Player, opening: str = ''):
        assert cross_player.get_sign() == Sign.CROSS
        assert circle_player.get_sign() == Sign.CIRCLE
        self._cross_player = cross_player
        self._circle_player = circle_player
        self._game = game
        self._command_log = []
        self._opening = copy.deepcopy(opening)

    def _get_player_to_move(self) -> Player:
        if self._game.get_sign_to_move() == Sign.CROSS:
            return self._cross_player
        else:
            return self._circle_player

    def _swap2board(self) -> None:
        def swap_players() -> None:
            tmp = self._cross_player
            self._cross_player = self._circle_player
            self._circle_player = tmp
            self._cross_player.set_sign(Sign.CROSS)
            self._circle_player.set_sign(Sign.CIRCLE)

        '''cross (black) player places first three stones'''
        black_opening = self._cross_player.swap2board([])
        for m in black_opening:
            self._game.make_move(m)

        '''circle (white) player responds to the 3-stone opening'''
        white_response = self._circle_player.swap2board(black_opening)
        if type(white_response) == str:
            assert str(white_response) == 'SWAP'
            swap_players()
            return
        else:
            assert type(white_response) == list
            for m in white_response:
                self._game.make_move(m)

            if len(white_response) == 1:  # only 4th move was returned
                return
            elif len(white_response) == 2:  # 4th and 5th moves was returned
                black_decision = self._cross_player.swap2board(black_opening + white_response)
                if type(black_decision) == str:
                    assert str(black_decision) == 'SWAP'
                    swap_players()
                    return
                else:
                    assert type(black_decision) == list and len(black_decision) == 1
                    self._game.make_move(black_decision[0])
                    return
            else:
                raise Exception('too many balancing stones')

    def play_game(self) -> GameOutcome:
        self._cross_player.start(self._game.rows(), self._game.cols(), self._game.rules())
        self._circle_player.start(self._game.rows(), self._game.cols(), self._game.rules())

        if self._opening == 'swap2':
            self._swap2board()
        elif len(self._opening) > 0:
            moves = self._opening.split(' ')
            for move in moves:
                tmp = move.split(',')
                self._game.make_move(Move(int(tmp[0]), int(tmp[1]), self._game.get_sign_to_move()))
        '''now the opening is prepared'''

        first_move = self._get_player_to_move().board(self._game.get_played_moves())
        self._game.make_move(first_move)
        print('move', self._game.number_of_moves())
        print(self._game.to_string())

        second_move = self._get_player_to_move().board(self._game.get_played_moves())
        self._game.make_move(second_move)
        print('move', self._game.number_of_moves())
        print(self._game.to_string())

        '''now both players got board state and can make moves'''
        while self._game.get_outcome() == GameOutcome.NO_OUTCOME:
            move = self._get_player_to_move().turn(self._game.get_last_move())
            self._game.make_move(move)
            print('move', self._game.number_of_moves())
            print(self._game.to_string())

        print(self._game.get_outcome())
        self.cleanup()
        return self._game.get_outcome()

    def cleanup(self) -> None:
        self._cross_player.end()
        self._circle_player.end()

    def generate_pgn(self) -> str:
        result = '[White \'' + self._cross_player.get_name() + '\']\n'
        result += '[Black \'' + self._circle_player.get_name() + '\']\n'
        outcome = self._game.get_outcome()
        if outcome == GameOutcome.CROSS_WIN:
            tmp = '1-0'
        elif outcome == GameOutcome.CIRCLE_WIN:
            tmp = '0-1'
        elif outcome == GameOutcome.DRAW:
            tmp = '1/2-1/2'
        else:
            return ''  # TODO maybe it's better to throw an exception instead of returning empty PGN?
        result += '[Result ' + tmp + ']\n'
        result += '\n'
        result += '1. d4 d5 ' + tmp + '\n'
        return result

    def draw(self, size: int = 15) -> np.ndarray:
        height = (1 + 6 + self._game.rows() + 1) * size
        width = (1 + self._game.cols() + 1) * size
        result = np.zeros((height, width, 3), dtype=np.uint8)
        line_thickness = max(1, size // 10)

        '''fill background'''
        cv2.rectangle(result, (0, 0), (width, height), color=(192, 192, 192), thickness=-1)

        '''highlight side to move'''
        if self._cross_player.is_on_move():
            cv2.rectangle(result, (0, int(0.5 * size)), (width, int((0.5 + 3) * size)), color=(224, 224, 224), thickness=-1)
        if self._circle_player.is_on_move():
            cv2.rectangle(result, (0, int((0.5 + 3) * size)), (width, int((0.5 + 3 + 3) * size)), color=(224, 224, 224), thickness=-1)

        def summarize_player(player: Player, x: int, y: int, color: tuple) -> None:
            text1 = player.get_name() + ' : ' + str(round(player.get_time_left(), 1)) + 's'
            text2 = str(player.get_memory() // (1024 * 1024)) + 'MB, ' + player.get_evaluation()
            cv2.putText(result, text1, (y, x - int(1.5 * size)), cv2.QT_FONT_NORMAL, 0.8, color=color, thickness=1)
            cv2.putText(result, text2, (y, x), cv2.QT_FONT_NORMAL, 0.6, color=color, thickness=1)

        '''print info about players'''
        summarize_player(self._cross_player, 3 * size, int(0.5 * size), (255, 0, 0))
        summarize_player(self._circle_player, 6 * size, int(0.5 * size), (0, 0, 255))

        '''draw board lines'''
        for i in range(self._game.rows()):
            for j in range(self._game.cols()):
                x0 = (1 + 6 + i) * size
                y0 = (1 + j) * size
                cv2.rectangle(result, (y0, x0), (y0 + size, x0 + size), color=(0, 0, 0), thickness=1)

        '''highlight last move'''
        last_move = self._game.get_last_move()
        if last_move is not None:
            x0 = (1 + 6 + last_move.row) * size
            y0 = (1 + last_move.col) * size
            cv2.rectangle(result, (y0, x0), (y0 + size, x0 + size), color=(0, 255, 255), thickness=1)

        '''draw all moves'''
        moves = self._game.get_played_moves()
        for move in moves:
            x0 = (1 + 6 + move.row) * size
            y0 = (1 + move.col) * size
            if move.sign == Sign.CROSS:
                cv2.line(result, (y0 + size // 10, x0 + size // 10), (y0 + size - size // 10, x0 + size - size // 10), color=(255, 0, 0), thickness=line_thickness)
                cv2.line(result, (y0 + size - size // 10, x0 + size // 10), (y0 + size // 10, x0 + size - size // 10), color=(255, 0, 0), thickness=line_thickness)
            else:
                cv2.circle(result, (y0 + size // 2, x0 + size // 2), (size * 4 // 10), color=(0, 0, 255), thickness=line_thickness)
        return result

    def text_summary(self) -> str:
        pass
