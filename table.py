from deck import Deck, Card
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
        self.team1_sets = {}  # // {suit: [card_set, card_set]}
        self.team2_sets = {}
        self.team1_hands = 0
        self.team2_hands = 0
        self.team1 = []
        self.team2 = []
        self.trash = []
        self.deck = deck
        self.game_over = False

        if len(players) % 2 != 0 or len(new_hands) % 2 != 0:
            raise ValueError("Number of players and new_hands must be even.")

        for _ in range(len(players)):
            if _ % 2 == 0:
                self.team1.append(players[_])
            else:
                self.team2.append(players[_])

    def __repr__(self):
        return f"Team 1: {self.team1},\n\nTeam 1 sets: {self.team1_sets},\n\nTeam 2: {self.team2},\n\n Team 2 sets: {self.team2_sets},\n\nTrash: {self.trash},\n\nDeck: {self.deck},\n\n# Cards in Deck: {len(self.deck.cards)},\n\nNew Hands: {self.new_hands}\n\n"

    def __str__(self):
        return f"Team 1: {self.team1},\n\nTeam 1 sets: {self.team1_sets},\n\nTeam 2: {self.team2},\n\n Team 2 sets: {self.team2_sets},\n\nTrash: {self.trash},\n\nDeck: {self.deck},\n\n# Cards in Deck: {len(self.deck.cards)},\n\nNew Hands: {self.new_hands}\n\n"

    def _shuffle_players(self):
        random.shuffle(self.players)

    def _get_team_set(self, player):
        if player in self.team1:
            return self.team1_sets
        else:
            return self.team2_sets

    def _get_team(self, player):
        if player in self.team1:
            return "1"
        else:
            return "2"

    def _team_has_clean_canastra(self, player):
        team = self._get_team(player)
        if team == "1":
            team_set = self.team1_sets
        else:
            team_set = self.team2_sets

        for suit in team_set:
            for s in team_set[suit]:
                if s._is_clean() == False:
                    return False
        return True

    def table(self, current_player):
        return f"Sets:\n\nTeam1: {self.team1_sets}\n\nTeam2: {self.team2_sets}\n\nTrash: {self.trash}\n\n# Cards in Deck: {len(self.deck.cards)}\n\nNew Hands: {len(self.new_hands)}\n\n{current_player.name}'s hand: {sorted(current_player.hand)}\n\n"
