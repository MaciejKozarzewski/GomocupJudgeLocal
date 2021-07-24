from __future__ import annotations
from threading import Thread
import os
import json
import cv2
import numpy as np
import time
from Match import Match
from Board import Board, Move, Sign
from Player import Player


class PlayingThread(Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._is_running = True
        self._match = None
        self.start()

    def draw(self) -> np.ndarray:
        if self._match is not None:
            return self._match.draw(30)
        else:
            return np.zeros((1, 1), dtype=np.uint8)

    def _play_game(self, cfg_cross: dict, cfg_circle: dict, opening: str) -> None:
        self._match = Match(Board(self._config['game_config']), Player(cfg_cross), Player(cfg_circle), opening)
        self._match.play_game()

    def run(self) -> None:
        while self._is_running:
            self._play_game(self._config['player_1'], self._config['player_2'], 'swap2')
            print(self._match.generate_pgn())
            time.sleep(5.0)
            self._play_game(self._config['player_2'], self._config['player_1'], 'swap2')

            self._is_running = False


class Tournament:
    def __init__(self, working_dir: str):
        if not os.path.exists(working_dir):
            os.mkdir(working_dir)

        if not os.path.exists(working_dir + 'config.json'):
            print('creating default config')
            with open(working_dir + 'config.json', 'w') as file:
                file.write(json.dumps(self._create_default_config(), indent=4))
            exit(0)

        print('loading config file')
        with open(working_dir + 'config.json', 'r') as file:
            self._config = json.loads(file.read())
        self._config['working_dir'] = working_dir
        self._game_outcomes = []
        self._threads = []
        for i in range(self._config['tournament_config']['games_in_parallel']):
            self._threads.append(PlayingThread(self._config))

    def draw(self) -> None:
        img = self._threads[0].draw()
        cv2.imshow('preview', img)
        cv2.waitKey(100)
        # cv2.destroyWindow('preview')

    @staticmethod
    def _create_default_config() -> dict:
        def create_default_player_config() -> dict:
            return {'command': '...',
                    'name': '...',
                    'timeout_turn': 5.0,  # in seconds
                    'timeout_match': 120.0,  # in seconds
                    'max_memory': 350 * 1024 * 1024,  # in bytes
                    'folder': './',
                    'allow_pondering': False,
                    'tolerance': 1.0,  # in seconds
                    'working_dir': './'}

        result = {'game_config': {'rows': 20,
                                  'cols': 20,
                                  'rules': 'freestyle'},
                  'tournament_config': {'games_to_play': 10,
                                        'games_in_parallel': 4,
                                        'visualise': True},
                  'player_1': create_default_player_config(),
                  'player_2': create_default_player_config()}

        return result


if __name__ == '__main__':
    # player_1_config = {'command': '/home/maciek/Desktop/AlphaGomoku5/pbrain-AlphaGomoku_cpu.out',
    #                    'name': 'AlphaGomoku_5_0_1',
    #                    'timeout_turn': 5.0,  # in seconds
    #                    'timeout_match': 120.0,  # in seconds
    #                    'max_memory': 1024 * 1024 * 1024,  # in bytes
    #                    'folder': './',
    #                    'allow_pondering': False}
    #
    # player_2_config = {'command': '/home/maciek/Desktop/AlphaGomoku4/pbrain-AlphaGomoku64_cpu',
    #                    'name': 'AlphaGomoku_4_0_0',
    #                    'timeout_turn': 5.0,  # in seconds
    #                    'timeout_match': 120.0,  # in seconds
    #                    'max_memory': 1024 * 1024 * 1024,  # in bytes
    #                    'folder': './',
    #                    'allow_pondering': False}
    #
    # games_in_parallel = 1
    # board_rows = 20
    # board_cols = 20
    # rules = GameRules.FREESTYLE
    # pass
    import sys
    import logging

    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    tournament = Tournament('/home/maciek/Desktop/tournament/')
    while True:
        tournament.draw()
