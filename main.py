from player import Player
from deck import Deck
from table import Table
import pdb

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

current_player = player1
while game.game_over == False:
    current_player.played = False
    print(
        f"\nCurrent player: {current_player.name}, Team: {current_player._get_team(game)}\n",
        "\n",
        "\n",
    )
    print("************************   Table   **********************: \n", "\n")
    print(f"{game.table(current_player)}\n")

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
    current_player.hand = sorted(current_player.hand)
    print(f"\nCurrent player Hand: {current_player.hand}\n")

    # // SECOND MOVE: player play cards or move to discard
    while current_player.played == False:
        cards = input(
            f'\nPlay a single or a set or type "d" to move to discard\nchoose a card from hand\n ex. "1" for {current_player.hand[0]}, "2" for {current_player.hand[1]}, and "1,2,3" for a set): '
        )

        # // player wants to discard
        if cards == "d":
            # // THIRD MOVE: player discards a card
            card_to_trash = input(
                f"\nWhich card to trash? ({current_player.hand[0]} = 1, and so on...):  "
            )
            if card_to_trash == "":
                print("No card selected. Try again.")
                continue
            card_to_trash = current_player.get_card(card_to_trash)
            confirmation = input(
                f"are you sure you want to discard {card_to_trash}? (y/n): "
            )
            if confirmation == "n":
                continue
            else:
                current_player.played = True
                discarded = current_player.discard(card_to_trash)
                game.trash.append(discarded)
                break

        # * since we are using indexes, we need to sort the hand
        current_player.hand = sorted(current_player.hand)
        selected_cards = sorted(cards.split(","))

        # ! make sure cards are not empty
        if len(selected_cards) < 0:
            print("No cards selected. Try again.")
            continue
        # ! make sure input is valid
        elif len(selected_cards) > len(current_player.hand):
            print("Too many cards selected. Try again.")
            continue

        # ! grab cards from hand unsing indexes
        print(f"number in hand of selected cards : {selected_cards}")
        got_cards = False
        for i in range(1, len(selected_cards) + 1):
            try:
                selected_cards[i - 1] = int(selected_cards[i - 1])
                c = current_player.get_card(selected_cards[i - 1])
                selected_cards[i - 1] = c
            except ValueError:
                print("\nInvalid input. Try again with numbers separated by commas.")
                break
            got_cards = True

        if got_cards == False:
            continue

        print(f"\ncards selected: {selected_cards}")
        # ! grab the team set state
        team_set = game._get_team_set(current_player)

        if len(selected_cards) >= 3:
            # // are cards valid?
            valid = current_player._is_play_valid(selected_cards)
            if valid == False:
                continue

            # // new or existing set?
            suit = selected_cards[-1].suit
            new_or_existing = input("\nNew set or add to existing set? (n/e): ")
            if new_or_existing == "n":
                current_player.drop_set(selected_cards, suit, game)
            else:
                index_of_set = input(f"\nWhich set? (first = 0) :\n ${team_set[suit]} ")
                extended = current_player.can_extend_set(
                    selected_cards, index_of_set, game
                )
                if extended == False:
                    continue
        else:
            # // is card valid?
            valid = current_player._is_play_valid(selected_cards)
            if valid == False:
                continue

            # // single card to existing set?
            card = selected_cards[0]
            if team_set.get(card.suit) == None:
                print("No sets of that suit to add. Try again.")
                continue

            set_to_add = input(f"\nWhich set? (first = 0) :\n ${team_set[card.suit]} ")
            current_player.extend_set(selected_cards, team_set[suit][set_to_add], game)

        # // player needs new hand after move to coninue or game over?
        chin = current_player.is_over_or_new_hands(game)
        if chin == True:
            game.game_over = True
            break

        print(f"\nCurrent player Hand: {current_player.hand}\n")

        # // keep playing or move to discard?
        more_plays = input("\nPlay more cards? (y/n): ")
        if more_plays == "y":
            continue

        else:
            # // THIRD MOVE: player discards a card
            card_to_trash = input(
                f"\nWhich card to trash? ({current_player.hand[0]} = 1, and so on...):  "
            )
            if card_to_trash == "":
                print("No card selected. Try again.")
                continue
            card_to_trash = current_player.get_card(card_to_trash)
            confirmation = input(
                f"are you sure you want to discard {card_to_trash}? (y/n)"
            )
            if confirmation == "n":
                continue
            else:
                discarded = current_player.discard(card_to_trash)
                game.trash.append(discarded)
                current_player.played = True

                chin = current_player.is_over_or_new_hands(game)
                if chin == True:
                    game.game_over = True
                    break

    if game.game_over == True:
        break

    # // next player
    if current_player is player1:
        current_player = player2
    elif current_player is player2:
        current_player = player3
    elif current_player is player3:
        current_player = player4
    else:
        current_player = player1

# // after game is over sum the points and declare the winner

team1_points = 0
team2_points = 0

for suit in game.team1_sets:
    for s in game.team1_sets[suit]:
        team1_points += s._get_points()

for suit in game.team2_sets:
    for s in game.team2_sets[suit]:
        team2_points += s._get_points()

if team1_points > team2_points:
    print(f"\n\nTeam 1 wins with {team1_points} points!")
elif team2_points > team1_points:
    print(f"\n\neam 2 wins with {team2_points} points!")
else:
    print(f"\n\nTeam 1 and Team 2 are tied with {team1_points} points!")
