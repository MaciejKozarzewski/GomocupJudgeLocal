from __future__ import annotations
from threading import Thread, Lock
import signal
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
from Board import Board, Sign, GameOutcome
from Player import Player
from exceptions import Timeouted, Crashed, MadeFoulMove, MadeIllegalMove, TooMuchMemory, Interrupted


class GameConfig:
    def __init__(self, black_player: str, white_player: str, opening: str, saved_state: str = '', index: int = None):
        self.black_player = copy.deepcopy(black_player)
        self.white_player = copy.deepcopy(white_player)
        self.opening = copy.deepcopy(opening)
        self.outcome = GameOutcome.NO_OUTCOME
        self.saved_state = copy.deepcopy(saved_state)
        self.index = index
        self.pgn = ''
        self.in_progress = False

    def save(self) -> str:
        return self.black_player + ':' + self.white_player + ':' + self.opening + ':' + str(self.outcome) + ':' + self.saved_state

    @staticmethod
    def load(text: str) -> GameConfig:
        tmp = text.strip('\n').split(':')
        assert len(tmp) == 5
        result = GameConfig(tmp[0], tmp[1], tmp[2], tmp[4])
        result.outcome = GameOutcome.from_string(tmp[3])
        return result


class PlayingThread(Thread):
    def __init__(self, manager: Tournament):
        super().__init__()
        self._manager = manager
        self._full_config = manager.get_config()
        self._is_running = True
        self._match = None

    def draw(self, size: int, force_refresh: bool = False) -> Optional[np.ndarray]:
        if self._match is not None:
            self._match.draw(size, force_refresh)
            return self._match.get_frame()
        else:
            return None

    def _play_game(self, config: GameConfig) -> GameConfig:
        board = Board(self._full_config['game_config'])
        player1 = Player(self._full_config[config.black_player])
        player2 = Player(self._full_config[config.white_player])
        self._match = Match(board, player1, player2, config.opening)
        self._match.load_state(config.saved_state)
        try:
            config.outcome = self._match.play_game()
            config.saved_state = ''
        except (Timeouted, Crashed, MadeFoulMove, MadeIllegalMove, TooMuchMemory) as e:
            logging.warning(str(e))
            config.saved_state = str(e)
            if e.sign == Sign.BLACK:
                config.outcome = GameOutcome.WHITE_WIN
            else:
                config.outcome = GameOutcome.BLACK_WIN
        except Interrupted as e:
            logging.warning(str(e))
            config.saved_state = 'in progress = ' + self._match.save_state()
        return config

    def run(self) -> None:
        while self._is_running:
            cfg = self._manager.get_game_to_play()
            if cfg is None:
                self._is_running = False
                break
            game_record = self._play_game(cfg)
            game_record.pgn = self._match.generate_pgn()
            game_record.in_progress = False
            self._manager.finish_gamed(game_record)
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
        self._is_running = False
        self._started_games = 0
        self._finished_games = 0
        self._tournament_lock = Lock()
        self._games = self._prepare_games()
        self._save_games()
        self._pgn = self._load_pgn()

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
                    result[i] = result[i].replace('\n', '').strip()
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
                    tmp = GameConfig.load(line)
                    result.append(tmp)
        else:
            print('creating new tournament state')
            openings = self._load_openings(self._config['openings'])
            for i in range(0, self._config['games_to_play'], 2):
                op = openings[(i // 2) % len(openings)]
                '''schedule two games with the same opening, but with players having different colors'''
                result.append(GameConfig('player_1', 'player_2', op))
                if i + 1 < self._config['games_to_play']:  # for odd number of games to play
                    result.append(GameConfig('player_2', 'player_1', op))

        for i in range(len(result)):
            result[i].index = i
            if result[i].outcome != GameOutcome.NO_OUTCOME:
                self._finished_games += 1
        return result

    def _save_games(self) -> None:
        with open(self._config['working_dir'] + '/games.txt', 'w') as file:
            for game in self._games:
                file.write(game.save() + '\n')

    def _save_pgn(self) -> None:
        with open(self._config['working_dir'] + '/result.pgn', 'w') as file:
            file.write(self._pgn)

    def _load_pgn(self) -> str:
        result = ''
        if os.path.exists(self._config['working_dir'] + '/result.pgn'):
            with open(self._config['working_dir'] + '/result.pgn', 'r') as file:
                result = file.read()
        return result

    def get_summary(self) -> str:
        result = ''
        result += str(self._started_games) + ' games started\n'
        result += str(self._finished_games) + ' games finished\n'

        wins = 0
        draws = 0
        losses = 0
        for game in self._games:
            if game.outcome == GameOutcome.DRAW:
                draws += 1
            elif game.outcome == GameOutcome.BLACK_WIN:
                if game.black_player == 'player_1':
                    wins += 1
                else:
                    losses += 1
            elif game.outcome == GameOutcome.WHITE_WIN:
                if game.black_player == 'player_2':
                    wins += 1
                else:
                    losses += 1

        result += self._config['player_1']['command'] + ' = ' + str(wins) + ':' + str(draws) + ':' + str(losses) + '\n'
        result += self._config['player_2']['command'] + ' = ' + str(losses) + ':' + str(draws) + ':' + str(wins) + '\n'
        return result

    def start(self) -> None:
        self._is_running = True
        for t in self._threads:
            t.start()

    def get_game_to_play(self) -> Optional[GameConfig]:
        with self._tournament_lock:
            for game in self._games:
                if game.outcome == GameOutcome.NO_OUTCOME and not game.in_progress:
                    game.in_progress = True
                    self._started_games += 1
                    return copy.deepcopy(game)
            return None

    def finish_gamed(self, game: GameConfig) -> None:
        with self._tournament_lock:
            self._games[game.index] = game
            self._pgn += game.pgn
            self._finished_games += 1
            self._save_games()
            self._save_pgn()
            print(self.get_summary())

    def get_config(self) -> dict:
        return copy.deepcopy(self._config)

    def draw(self, size: int, force_reshresh: bool = False) -> None:
        height = 0
        width = 0
        imgs = []
        for t in self._threads:
            tmp = t.draw(size, force_reshresh)
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
                  'games_in_parallel': 1,
                  'openings': 'openings_freestyle.txt',  # can also be 'swap2'
                  'visualise': True,
                  'game_config': {'rows': 20,
                                  'cols': 20,
                                  'rules': 'freestyle'},
                  'player_1': create_default_player_config(),
                  'player_2': create_default_player_config()}

        return result

    def is_running(self) -> bool:
        with self._tournament_lock:
            return self._is_running and self._finished_games < self._config['games_to_play']

    def stop(self) -> None:
        with self._tournament_lock:
            self._is_running = False


def run_tournament(path: str, draw_boards: bool = False) -> None:
    tournament = Tournament(path)

    def signal_handler(sig, frame):
        logging.info('Requesting interruption, this may take a while...')
        tournament.stop()

    signal.signal(signal.SIGINT, signal_handler)

    tournament.start()
    while tournament.is_running():
        if draw_boards:
            tournament.draw(30, True)
            cv2.imshow('preview', tournament.get_frame())
            cv2.waitKey(100)
        else:
            time.sleep(1)

    tournament.cleanup()
    if draw_boards:
        cv2.destroyWindow('preview')


if __name__ == '__main__':
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    run_tournament('somepath')
    exit(0)
