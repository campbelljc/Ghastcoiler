import random
import logging

from typing import Optional

from game.player_board import PlayerBoard
from minions.base import Minion


class GameInstance:
    def __init__(self, player_board_0: PlayerBoard, player_board_1: PlayerBoard, player_turn: Optional[int] = None):
        """Instance of a single game rollout

        Arguments:
            player_board_0 {PlayerBoard} -- Player board of the first player
            player_board_1 {PlayerBoard} -- Player board of the second player

        Keyword Arguments:
            player_turn {Optional[int]} -- Player that starts, if None choose at random (default: {None})
        """
        self.player_board = {0: player_board_0, 1: player_board_1}
        self.player_turn = player_turn if player_turn else random.randint(0, 1)
        self.turn = 0

    def log_current_game(self):
        """Log current game state"""
        self.update_attack_and_defense()
        logging.debug("Player 0 board:")
        logging.debug(self.player_board[0].minions_string())
        logging.debug("Player 1 board:")
        logging.debug(self.player_board[1].minions_string())

    def __str__(self):
        """String representation of current game state

        Returns:
            string -- Representation
        """
        self.update_attack_and_defense()
        return_string = "Player 0:\n"
        return_string += str(self.player_board[0]) + "\n\n"
        return_string += "Player 1:\n"
        return_string += str(self.player_board[1])
        return return_string

    def update_attack_and_defense(self):
        """Update the attack and defense of all minions, this will be replaced soon"""
        for minion in self.player_board[0].get_minions():
            minion.update_attack_and_defense(self.player_board[0], self.player_board[1])
        for minion in self.player_board[1].get_minions():
            minion.update_attack_and_defense(self.player_board[1], self.player_board[0])

    def attacking_player_board(self):
        """Return board of currently attacking player

        Returns:
            PlayerBoard -- PlayerBoard of the current attacking player
        """
        return self.player_board[self.player_turn]

    def defending_player_board(self):
        """Return board of currently defending player

        Returns:
            PlayerBoard -- PlayerBoard of the current defending player
        """
        return self.player_board[1 - self.player_turn]

    def finished(self):
        """Check if the game is finished

        Returns:
            bool -- Is the game finished?
        """
        return len(self.player_board[0].minions) == 0 or len(self.player_board[1].minions) == 0

    def deal_damage(self, minion, board, amount, poisonous):
        """Deal damage to minion

        Arguments:
            minion {Minion} -- Minion that is dealt damage
            board {PlayerBoard} -- Player board of which the minion belongs to
            amount {int} -- Amount of damage dealt
            poisonous {bool} -- Whether it is poisonous damage
        """
        divine_shield_popped = minion.receive_damage(amount, poisonous)
        if divine_shield_popped:
            logging.debug("Divine shield popped")
            board.divine_shield_popped()

    def kill(self, minion: Minion, minion_board: PlayerBoard, opposing_board: PlayerBoard, minion_defending_player: bool):
        """Kill a minion off and update board using deathrattles and other triggers

        Arguments:
            minion {Minion} -- Minion that will die
            minion_board {PlayerBoard} -- Player board belonging to the minion
            opposing_board {PlayerBoard} -- Board opposing of the minion that dies
            minion_defending_player {bool} -- Whether the minion died is on the defending side for trigger orders
        """
        # TODO: Baron
        if minion_defending_player:
            opposing_board.remove_minion(minion)
        else:
            minion_board.remove_minion(minion)
        for deathrattle in minion.deathrattles:
            if minion_defending_player:
                deathrattle.trigger(minion, opposing_board, minion_board)
            else:
                deathrattle.trigger(minion, minion_board, opposing_board)
        self.check_deaths(minion_board, opposing_board)

    def check_deaths(self, attacking_player_board: PlayerBoard, defending_player_board: PlayerBoard):
        """Check deaths on both sides

        Arguments:
            attacking_player_board {PlayerBoard} -- Player board of attacking player
            defending_player_board {PlayerBoard} -- Player board of defending player
        """
        for minion in attacking_player_board.get_minions():
            if minion.check_death(attacking_player_board, defending_player_board):
                self.kill(minion, attacking_player_board, defending_player_board, minion_defending_player=False)
                return
        for minion in defending_player_board.get_minions():
            if minion.check_death(defending_player_board, attacking_player_board):
                self.kill(minion, attacking_player_board, defending_player_board, minion_defending_player=True)
                return

    def attack(self, attacking_minion: Minion, defending_minion: Minion):
        """Let one minion attack the other

        Arguments:
            attacking_minion {Minion} -- Minion that attacks
            defending_minion {Minion} -- Minion that is attacked
        """
        # TODO: Cleave
        current, other = self.attacking_player_board(), self.defending_player_board()
        logging.debug(f"{attacking_minion.minion_string()} attacks {defending_minion.minion_string()}")
        attacking_minion.on_attack()
        attacking_minion_attack, _ = attacking_minion.total_attack_and_defense(current, other)
        defending_minion_attack, _ = defending_minion.total_attack_and_defense(other, current)
        self.deal_damage(attacking_minion, current, defending_minion_attack, defending_minion.poisonous)
        self.deal_damage(defending_minion, other, attacking_minion_attack, attacking_minion.poisonous)

    def calculate_score_player_0(self):
        """Calculate final score from player 0 perspective, negative is lost by X, 0 is a tie and positive is won by X

        Returns:
            int -- Amount by which player 0 won or lost
        """
        if len(self.player_board[0].minions) == 0:
            return - self.player_board[1].score()
        else:
            return self.player_board[0].score()

    def start(self):
        """Start game instance rollout

        Returns:
            int -- Final score from player 0 perspective
        """
        current = self.attacking_player_board()
        other = self.defending_player_board()
        for minion in current.get_minions():
            minion.at_beginning_game(self, True, current, other)
        for minion in other.get_minions():
            minion.at_beginning_game(self, False, other, current)
        while not self.finished():
            self.turn += 1
            logging.debug(f"Turn {self.turn} has started, player {self.player_turn} will attack")
            self.log_current_game()
            logging.debug('-----------------')
            attacking_minion = self.attacking_player_board().select_attacking_minion()
            defending_minion = self.defending_player_board().select_defending_minion()
            self.attack(attacking_minion, defending_minion)
            self.check_deaths(self.attacking_player_board(), self.defending_player_board())
            logging.debug("=================")
            self.player_turn = 1 - self.player_turn
        logging.debug(self.calculate_score_player_0())
        return self.calculate_score_player_0()
