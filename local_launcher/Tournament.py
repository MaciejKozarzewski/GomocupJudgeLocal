from local_launcher.game_rules import GameRules, Sign
from local_launcher.Player import Player


def create_player(config: dict) -> Player:
    return Player(sign=Sign.EMPTY,
                  command=config['command'],
                  name=config['name'],
                  timeout_turn=config['timeout_turn'],
                  timeout_match=config['timeout_match'],
                  max_memory=config['max_memory'],
                  folder=config['folder'],
                  allow_pondering=config['allow_pondering'])


if __name__ == '__main__':
    player_1_config = {'command': '/home/maciek/Desktop/AlphaGomoku5/pbrain-AlphaGomoku_cpu.out',
                       'name': 'AlphaGomoku_5_0_1',
                       'timeout_turn': 5.0,  # in seconds
                       'timeout_match': 120.0,  # in seconds
                       'max_memory': 1024 * 1024 * 1024,  # in bytes
                       'folder': './',
                       'allow_pondering': False}

    player_2_config = {'command': '/home/maciek/Desktop/AlphaGomoku4/pbrain-AlphaGomoku64_cpu',
                       'name': 'AlphaGomoku_4_0_0',
                       'timeout_turn': 5.0,  # in seconds
                       'timeout_match': 120.0,  # in seconds
                       'max_memory': 1024 * 1024 * 1024,  # in bytes
                       'folder': './',
                       'allow_pondering': False}

    games_in_parallel = 1
    board_rows = 20
    board_cols = 20
    rules = GameRules.FREESTYLE
    pass
