from player import Player
from deck import Deck
from table import Table

# ! time spent: 2h as of 11/29 11:20am

"""
  - Let's play Canastra!

  - This is the main file of the game. It will be responsible for the game loop and the game state.
"""

""" * Initial Setup :

  * Set the Number of players
  * Set the Number of new_hands (morto)
  * Set the Number of decks
"""

# ? default values: (4, 4, 4) -> 4 players, 4 new_hands, 4 decks
NUMBER_OF_PLAYERS = 4
NUMBER_OF_NEW_HANDS = 4
NUMBER_OF_DECKS = 4

deck = Deck(NUMBER_OF_DECKS)
deck._shuffle()

# // we need double the number of new_hands 1ea/player + 1ea/morto
new_hands = [hand for hand in deck._deal_new_hands(NUMBER_OF_DECKS + NUMBER_OF_PLAYERS)]

# print(f" these are the morto:\n{[for hand in new_hands]}\n")

names = [(input(f"Player {i+1} name: ")) for i in range(NUMBER_OF_PLAYERS)]

# // create players
players = [Player(i, names[i], new_hands[i]) for i in range(NUMBER_OF_PLAYERS)]

# // Start game state loop:
game = Table(players, deck, new_hands[NUMBER_OF_PLAYERS:])
print(f" this is the game state:\n{game}\n")

player1, player2, player3, player4 = (
    game.players[0],
    game.players[1],
    game.players[2],
    game.players[3],
)
