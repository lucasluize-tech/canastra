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
  all of the above are default values, but can be changed by the user.
  
"""

# ? default values: (4, 4, 4) -> 4 players, 4 new_hands, 4 decks
NUMBER_OF_PLAYERS = 4
NUMBER_OF_NEW_HANDS = 4
NUMBER_OF_DECKS = 4

deck = Deck(NUMBER_OF_DECKS)
deck._shuffle()

# // we need double the number of new_hands 1ea/player + 1ea/morto
new_hands = [hand for hand in deck._deal_new_hands(NUMBER_OF_DECKS + NUMBER_OF_PLAYERS)]

names = [(input(f"Player {i+1} name: ")) for i in range(NUMBER_OF_PLAYERS)]

# // create players
players = [Player(names[i], new_hands[i]) for i in range(NUMBER_OF_PLAYERS)]

# // initialize game state
game = Table(players, deck, new_hands[NUMBER_OF_PLAYERS:])
# print(f"\nThis is the game state:\n{game}\n")

player1, player2, player3, player4 = (
    game.players[0],
    game.players[1],
    game.players[2],
    game.players[3],
)

# // Start game state loop:
while game.game_over == False:
    current_player = player1
    current_player.played = False
    print(
        f"\nCurrent player: {current_player.name}, Team: {current_player._get_team(game)}\n",
        "\n",
        "\n",
    )
    print("************************   Table   **********************: \n", "\n")
    print(f"{game.table()}\n")

    # // FIRST MOVE : player draws a card or the trash
    move = input("Draw from deck or trash? (d/t): ")
    if move == "":
        print("No move selected. Try again.")
        continue
    if move == "d":
        current_player.draw(game.deck)
    else:
        if len(game.trash) == 0:
            print("Trash is empty. Draw from deck.")
            continue
        current_player.get_trash(game.trash)
        game.trash = []

    print(f"Current player Hand: {sorted(current_player.hand)}\n")

    # // SECOND MOVE: player play cards
    while current_player.played == False:
        cards = input(
            "Play a single or a set(3 or more cards same suit) \n(rank,suit  eg. set: Jack,C-Queen,C-King,C or single: Ace,C):"
        )
        cards = cards.split("-")
        print(f"cards selected: {cards}")
        # ! make sure cards are not empty
        if len(cards) < 0:
            print("No cards selected. Try again.")
            continue

        elif len(cards) >= 3:
            # // are cards valid?
            valid = current.player.is_play_valid(cards)
            if valid == False:
                continue

            # // new or existing set?
            new_or_existing = input("New set or add to existing set? (n/e): ")
            team_set = game._get_team_set(current_player)
            if new_or_existing == "n":
                suit = input("Which suit? (c,d,h,s): ")
                if suit == "c":
                    suit = "Clubs"
                elif suit == "d":
                    suit = "Diamonds"
                elif suit == "h":
                    suit = "Hearts"
                else:
                    suit = "Spades"
                current_player.drop_set(cards, suit, game)
            else:
                set_to_add = input(f"Which set? (first = 0) :\n ${team_set[suit]} ")
                current_player.extend_set(cards, team_set[suit][set_to_add], game)

        else:
            # // single card to existing set?
            set_to_add = input(f"Which set? (first = 0) :\n ${team_set[suit]} ")
            current_player.extend_set(cards, team_set[suit][set_to_add], game)

        more_plays = input("Play more cards? (y/n): ")
        if more_plays == "y":
            continue

        # // THIRD MOVE: player discards a card
        else:
            card_to_trash = input("Which card to trash? (rank,suit eg. Ace,S):  ")
            valid = current_player.is_play_valid(card_to_trash)
            current_player.discard(card_to_trash)
            game.trash.add(card_to_trash)
            # // player needs new hand or game over?
            if len(current_player.hand) == []:
                current_player.get_new_hand(game.new_hands.pop())
            current.player.played = True

    if current_player == player1:
        current_player = player2
    elif current_player == player2:
        current_player = player3
    elif current_player == player3:
        current_player = player4
    else:
        current_player = player1
