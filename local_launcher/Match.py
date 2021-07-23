from local_launcher.Game import Game, Move, Sign, GameRules, GameOutcome
from local_launcher.Player import Player
import copy
import time
import sys
import logging
import signal


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

        return self._game.get_outcome()

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


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    cross_player = Player(sign=Sign.CROSS,
                          command='/home/maciek/Desktop/AlphaGomoku5/pbrain-AlphaGomoku_cpu.out',
                          name='AlphaGomoku_5_0_1',
                          timeout_turn=5.0,
                          timeout_match=120.0,
                          max_memory=1024 * 1024 * 1024,
                          folder='./',
                          allow_pondering=False)

    circle_player = Player(sign=Sign.CIRCLE,
                           command='/home/maciek/Desktop/AlphaGomoku4/pbrain-AlphaGomoku64_cpu',
                           name='AlphaGomoku_4_0_0',
                           timeout_turn=5.0,
                           timeout_match=120.0,
                           max_memory=1024 * 1024 * 1024,
                           folder='./',
                           allow_pondering=False)


    def signal_handling(signum, frame):
        print('stopping all players...')
        cross_player.end()
        circle_player.end()
        time.sleep(5.0)
        print('exiting...')
        sys.exit()


    signal.signal(signal.SIGINT, signal_handling)

    game = Game(15, 15, GameRules.STANDARD)

    match = Match(game, cross_player, circle_player)
    outcome = match.play_game()
    print(outcome)
