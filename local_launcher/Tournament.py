from __future__ import annotations
from threading import Thread
import os
import json
import cv2
import numpy as np
from typing import Optional
import time
import sys
import logging
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

    def draw(self) -> Optional[np.ndarray]:
        if self._match is not None:
            self._match.draw(30)
            return self._match.get_frame()
        else:
            return None

    def _play_game(self, cfg_cross: dict, cfg_circle: dict, opening: str) -> None:
        self._match = Match(Board(self._config['game_config']), Player(cfg_cross), Player(cfg_circle), opening)
        self._match.play_game()

    def run(self) -> None:
        while self._is_running:
            self._play_game(self._config['player_1'], self._config['player_2'], 'swap2')
            time.sleep(5.0)
            self._play_game(self._config['player_2'], self._config['player_1'], 'swap2')

            self._is_running = False

    def cleanup(self) -> None:
        if self._match is not None:
            self._match.cleanup()


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

        self._frame = None

    def draw(self) -> None:
        height = 0
        width = 0
        imgs = []
        for t in self._threads:
            tmp = t.draw()
            if tmp is None:
                return
            imgs.append(tmp)
            height = max(height, tmp.shape[0])
            width += tmp.shape[1]

        if self._frame is None:
            self._frame = np.zeros((height, width, 3), dtype=np.uint8)
        width = 0
        for img in imgs:
            self._frame[0:img.shape[0], width:width + img.shape[1], :] = img
            width += img.shape[1]

    def get_frame(self) -> np.ndarray:
        if self._frame is None:
            return np.zeros((1, 1, 3), dtype=np.uint8)
        else:
            return self._frame

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
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    tournament = Tournament('/home/maciek/Desktop/tournament/')

    while True:
        tournament.draw()
        cv2.imshow('preview', tournament.get_frame())
        cv2.waitKey(1000)
    cv2.destroyWindow('preview')
