from deck import Deck, Card, Trash
from player import Player
import random


class Table:
    """
    !This class will be responsible for the game loop and the game state.

    @param players: list of player Objects
    @param num_decks: number of decks
    @param num_new_hands: number of new hands

    """

    def __init__(self, players, deck, new_hands):
        self.players = players
        self.new_hands = new_hands
        self.team1_sets = []
        self.team2_sets = []
        self.team1 = []
        self.team2 = []
        self.trash = Trash()
        self.deck = deck

        if len(players) % 2 != 0 or len(new_hands) % 2 != 0:
            raise ValueError("Number of players and new_hands must be even.")

        for _ in range(len(players)):
            if _ % 2 == 0:
                self.team1.append(players[_])
            else:
                self.team2.append(players[_])

    def __repr__(self):
        return f"Team 1: {self.team1}, Team 1 sets: {self.team1_sets},\nTeam 2: {self.team2}\n, Team 2 sets: {self.team2_sets}\n, Trash: {self.trash}\n, Deck: {self.deck}\n, New Hands: {self.new_hands}\n"

    def __str__(self):
        return f"Team 1: {self.team1}, Team 1 sets: {self.team1_sets},\nTeam 2: {self.team2}\n, Team 2 sets: {self.team2_sets}\n, Trash: {self.trash}\n, Deck: {self.deck}\n, New Hands: {self.new_hands}\n"

    def _shuffle_players(self):
        random.shuffle(self.players)
