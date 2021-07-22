from local_launcher.Game import Game, Move, Sign
from local_launcher.Player import Player
from typing import Optional
import copy


class Match:
    def __init__(self, game: Game, cross_player: Player, circle_player: Player, opening: str = ''):
        self._cross_player = cross_player
        self._circle_player = circle_player
        self._game = game
        self._command_log = []
        self._opening = copy.deepcopy(opening)

    @staticmethod
    def _parse_move_from_string(msg: str, sign: Sign) -> Move:
        tmp = msg.split(',')
        assert len(tmp) == 2
        return Move(int(tmp[1]), int(tmp[0]), sign)

    @staticmethod
    def _is_message(msg: str) -> bool:
        return msg.startswith('MESSAGE') or msg.startswith('ERROR') or msg.startswith('UNKNOWN')

    def _write_message_to_player(self, player: Player, msg: str) -> None:
        self._command_log.append(msg)
        player.send(msg)

    def _read_message_from_player(self, player: Player) -> str:
        result = player.receive()
        self._command_log.append(result)
        return result

    def _get_response(self, player) -> str:
        while True:
            answer = self._read_message_from_player(player)
            if answer is None:
                raise Exception('player has not responded correctly')
            elif not self._is_message(answer):
                return answer

    def _start_player(self, player: Player) -> None:
        if self._game.is_square():
            self._write_message_to_player(player, 'START ' + str(self._game.rows()))
        else:
            self._write_message_to_player(player, 'RECSTART ' + str(self._game.cols()) + ',' + str(self._game.rows()))

        answer = self._get_response(player)
        if answer == 'OK':
            return
        else:
            raise Exception('player has not responded \'OK\' to START command')

    def _stop_player(self, player: Player) -> None:
        self._write_message_to_player(player, 'END')
        player.stop_process()

    def _send_info(self, player: Player, info: str) -> None:
        self._write_message_to_player(player, 'INFO ' + info)

    def _start_game(self, player: Player) -> Move:
        self._write_message_to_player(player, 'BOARD')
        for move in self._game.get_played_moves():
            assert move.sign != Sign.EMPTY
            if move.sign == player.get_sign():
                self._write_message_to_player(player, move.col + ',' + move.row + ',1')
            else:
                self._write_message_to_player(player, move.col + ',' + move.row + ',2')
        self._write_message_to_player(player, 'DONE')

        answer = self._get_response(player)
        tmp = answer.split(',')
        assert len(tmp) == 2
        return Move(int(tmp[1]), int(tmp[0]), player.get_sign())

    def swap2board(self) -> None:
        def swap_players() -> None:
            tmp = self._cross_player
            self._cross_player = self._circle_player
            self._circle_player = tmp

        current_player = self._cross_player  # cross is black, so it starts as first
        self._write_message_to_player(current_player, 'SWAP2BOARD')
        self._write_message_to_player(current_player, 'DONE')
        answer = self._get_response(current_player)

        '''parse and make first three moves'''
        opening = answer.split(' ')
        assert len(opening) == 3
        self._game.make_move(self._parse_move_from_string(opening[0], Sign.CROSS))
        self._game.make_move(self._parse_move_from_string(opening[1], Sign.CIRCLE))
        self._game.make_move(self._parse_move_from_string(opening[2], Sign.CROSS))

        current_player = self._circle_player
        self._write_message_to_player(current_player, 'SWAP2BOARD')
        for m in opening:
            self._write_message_to_player(current_player, m)
        self._write_message_to_player(current_player, 'DONE')
        answer = self._get_response(current_player)

        '''parse response to the opening'''
        if answer == 'SWAP':
            swap_players()
            return
        balancing = answer.split(' ')
        if len(balancing) == 1:  # circle player stays with its color and outputs 4th move
            self._game.make_move(self._parse_move_from_string(balancing[0], Sign.CIRCLE))
            return
        elif len(balancing) == 2:  # circle player places two stones
            self._game.make_move(self._parse_move_from_string(balancing[0], Sign.CIRCLE))
            self._game.make_move(self._parse_move_from_string(balancing[1], Sign.CROSS))
        else:
            raise Exception('incorrect number of moves')

        current_player = self._cross_player
        self._write_message_to_player(current_player, 'SWAP2BOARD')
        for m in opening:
            self._write_message_to_player(current_player, m)
        for m in balancing:
            self._write_message_to_player(current_player, m)
        self._write_message_to_player(current_player, 'DONE')
        answer = self._get_response(current_player)

        if answer == 'SWAP':
            swap_players()
        else:
            sixth_move = answer.split(' ')
            assert len(balancing) == 1
            self._game.make_move(self._parse_move_from_string(sixth_move[0], Sign.CIRCLE))

    def _make_move(self, player: Player) -> Optional[Move]:
        assert self._game.get_sign_to_move() == player.get_sign()

        last_move = self._game.get_last_move()
        self._write_message_to_player(player, 'TURN ' + str(last_move.col) + ' ' + str(last_move.row))

        while True:
            answer = self._read_message_from_player(player)
            if answer is None:
                return None
            elif not self._is_message(answer):
                tmp = answer.split(',')
                assert len(tmp) == 2
                return Move(int(tmp[1]), int(tmp[0]), player.get_sign())

    def play_game(self) -> None:
        if self._opening == 'swap2':
            pass
        else:
            pass
