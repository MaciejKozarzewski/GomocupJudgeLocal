from __future__ import annotations
from threading import Thread, Lock
import subprocess, shlex
import os
import json
import copy
import numpy as np
from typing import Optional
import time
import cv2
import sys
import logging
from Match import Match
from Board import Board, Move, Sign, GameOutcome, GameRules
from Player import Player


class PlayingThread(Thread):
    def __init__(self, manager: Tournament):
        super().__init__()
        self._manager = manager
        self._config = manager.get_config()
        self._is_running = True
        self._match = None

    def draw(self, size: int) -> Optional[np.ndarray]:
        if self._match is not None:
            self._match.draw(size)
            return self._match.get_frame()
        else:
            return None

    def _play_game(self, cfg_cross: dict, cfg_circle: dict, opening: str) -> GameOutcome:
        self._match = Match(Board(self._config['game_config']), Player(cfg_cross), Player(cfg_circle), opening)
        return self._match.play_game()

    def run(self) -> None:
        while self._is_running:
            idx, cfg = self._manager.get_game_to_play()
            if cfg is None:
                self._is_running = False
                break
            outcome = self._play_game(self._config[cfg[0]], self._config[cfg[1]], cfg[2])
            self._manager.finish_gamed(idx, outcome, self._match.generate_pgn())

            time.sleep(5.0)

    def cleanup(self) -> None:
        self._is_running = False
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
        self._started_games = 0
        self._finished_games = 0
        self._tournament_lock = Lock()
        self._games = self._prepare_games()
        self._save_games()
        self._pgn = ''

        self._threads = []
        for i in range(self._config['games_in_parallel']):
            self._threads.append(PlayingThread(self))

        self._frame = None

    def _load_openings(self, filename: str) -> list:
        if filename == 'swap2':
            return ['swap2'] * self._config['games_to_play']
        elif os.path.exists(self._config['working_dir'] + '/' + filename):
            with open(self._config['working_dir'] + '/' + filename) as file:
                result = file.readlines()
                for i in range(len(result)):
                    result[i] = result[i].replace('\n', '')
                return result
        else:
            raise Exception('could not read file with openings')

    def _prepare_games(self) -> list:
        result = []
        if os.path.exists(self._config['working_dir'] + '/games.txt'):
            print('found existing tournament state')
            with open(self._config['working_dir'] + '/games.txt', 'r') as file:
                lines = file.readlines()
                for line in lines:
                    tmp = line[:-1].split(':')
                    result.append([tmp[0], tmp[1], tmp[2], GameOutcome.from_string(tmp[3])])
        else:
            print('creating new tournament state')
            openings = self._load_openings(self._config['openings'])
            for i in range(0, self._config['games_to_play'], 2):
                op = openings[(i // 2) % len(openings)]
                '''schedule two games with the same opening, but with players having different colors'''
                result.append(['player_1', 'player_2', op, GameOutcome.NO_OUTCOME])
                if i + 1 < self._config['games_to_play']:  # for odd number of games to play
                    result.append(['player_2', 'player_1', op, GameOutcome.NO_OUTCOME])
        return result

    def _save_games(self) -> None:
        with open(self._config['working_dir'] + '/games.txt', 'w') as file:
            for line in self._games:
                ''' black player, white player, opening, outcome'''
                file.write(line[0] + ':' + line[1] + ':' + line[2] + ':' + str(line[3]) + '\n')

    def _save_pgn(self) -> None:
        with open(self._config['working_dir'] + '/result.pgn', 'w') as file:
            file.write(self._pgn)

    def get_summary(self) -> str:
        result = ''
        result += str(self._started_games) + ' games started\n'
        result += str(self._finished_games) + ' games finished\n'

        wins = 0
        draws = 0
        losses = 0
        for g in self._games:
            if g[3] == GameOutcome.DRAW:
                draws += 1
            elif g[3] == GameOutcome.BLACK_WIN:
                if g[0] == 'player_1':
                    wins += 1
                else:
                    losses += 1
            elif g[3] == GameOutcome.WHITE_WIN:
                if g[0] == 'player_2':
                    wins += 1
                else:
                    losses += 1

        result += self._config['player_1']['command'] + ' = ' + str(wins) + ':' + str(draws) + ':' + str(losses) + '\n'
        result += self._config['player_2']['command'] + ' = ' + str(losses) + ':' + str(draws) + ':' + str(wins) + '\n'
        return result

    def start(self) -> None:
        for t in self._threads:
            t.start()

    def get_game_to_play(self) -> Optional[tuple]:
        with self._tournament_lock:
            if self._started_games < self._config['games_to_play']:
                result = self._started_games, self._games[self._started_games]
                self._started_games += 1

                return result
            else:
                return -1, None

    def finish_gamed(self, idx: int, outcome: GameOutcome, pgn: str) -> None:
        with self._tournament_lock:
            self._games[idx][3] = outcome
            self._pgn += pgn + '\n'
            self._finished_games += 1
            self._save_games()
            self._save_pgn()
            print(self.get_summary())

    def get_config(self) -> dict:
        return copy.deepcopy(self._config)

    def draw(self, size: int) -> None:
        height = 0
        width = 0
        imgs = []
        for t in self._threads:
            tmp = t.draw(size)
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

    def cleanup(self) -> None:
        for t in self._threads:
            t.cleanup()

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

        result = {'games_to_play': 10,
                  'games_in_parallel': 4,
                  'openings': 'openings_freestyle.txt',  # can also be 'swap2'
                  'visualise': True,
                  'game_config': {'rows': 20,
                                  'cols': 20,
                                  'rules': 'freestyle'},
                  'player_1': create_default_player_config(),
                  'player_2': create_default_player_config()}

        return result


if __name__ == '__main__':
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    tournament = Tournament('/home/maciek/Desktop/tournament/')

    tournament.start()
    while True:
        tournament.draw(24)
        cv2.imshow('preview', tournament.get_frame())
        cv2.waitKey(1000)
    tournament.cleanup()
    cv2.destroyWindow('preview')
