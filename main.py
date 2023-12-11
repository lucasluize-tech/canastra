from player import Player
from deck import Deck
from table import Table
import pdb

# ! time spent: 20 hours so far

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
    print("************************   Table   **********************: \n", "\n")
    print(
        f"Current player: {current_player.name}, Team: {current_player._get_team(game)}",
        "\n",
        "\n",
    )
    print(f"{game.table(current_player)}\n")

    # // FIRST MOVE : player draws a card or the trash
    move = input("Draw from deck or trash? (d/t): ")
    if move != "d" and move != "t":
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
    print(f"\nHand: {current_player.hand}\n")
    print(f"hand: {[i for i in range(1,len(current_player.hand)+ 1)]}")

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
            if (
                card_to_trash == ""
                or int(card_to_trash) > len(current_player.hand)
                or card_to_trash.isdigit() == False
            ):
                print("No card selected. Try again.")
                continue

            card_to_trash = current_player.get_card(card_to_trash)
            confirmation = input(
                f"are you sure you want to discard {card_to_trash} (y/n)?: "
            )
            if confirmation == "n" and confirmation != "y":
                print("\nInvalid input. Try again.")
                continue
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
            print("\nNo cards selected. Try again.")
            continue
        # ! make sure input is valid
        elif len(selected_cards) > len(current_player.hand):
            print("\nToo many cards selected. Try again.")
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
            if new_or_existing != "n" and new_or_existing != "e":
                print("\nInvalid input. Try again.")
                continue
            if new_or_existing == "n":
                current_player.drop_set(selected_cards, suit, game)
            else:
                index_of_set = input(
                    f"\nWhich set? (first = 0) or enter to cancel :\n ${team_set[suit]} "
                )
                if index_of_set.isdigit() == False:
                    continue
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

            index_of_set = input(
                f"\nWhich set? (first = 0) or enter to cancel :\n ${team_set[suit]} "
            )
            if index_of_set.isdigit() == False:
                continue
            current_player.can_extend_set(
                selected_cards, team_set[suit][int(index_of_set)], game
            )

        # // player needs new hand after move to continue or game over?
        chin = current_player.is_over_or_new_hands(game)
        if chin == True:
            game.game_over = True
            break

        print(f"\nCurrent player Hand: {current_player.hand}\n")
        print(
            f"hand from {current_player.hand.index(current_player.hand[0])+1} to {current_player.hand.index(current_player.hand[-1])+1}"
        )

        # // keep playing or move to discard?
        more_plays = input("\nPlay more cards? (y/n): ")
        if more_plays != "n":
            continue

        else:
            # // THIRD MOVE: player discards a card
            card_to_trash = input(
                f"\nWhich card to trash? ({current_player.hand[0]} = 1, and so on...):  "
            )

            if (
                card_to_trash == ""
                or int(card_to_trash) > len(current_player.hand)
                or card_to_trash.isdigit() == False
            ):
                print("Invalid choice. Try again.")
                continue
            card_to_trash = current_player.get_card(card_to_trash)
            confirmation = input(
                f"are you sure you want to discard {card_to_trash}? (y/n)"
            )
            if confirmation != "y":
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

# // ********************** GAME OVER *********************************

# // First, for each card in team's hand remove from team's sets.

num_of_team1_cards_in_hand = len(game.players[0].hand) + len(game.players[2].hand)
num_of_team2_cards_in_hand = len(game.players[1].hand) + len(game.players[3].hand)

print(f"\nTeam1 has to discard: {num_of_team1_cards_in_hand} cards")
print(f"\nTeam2 has to discard: {num_of_team2_cards_in_hand} cards")

# * Team choses which cards to remove from sets if any
for player in game.players:
    player.played = False

all_players_removed = False
while all_players_removed == False:
    i = 0
    cur_player = game.players[i]
    while cur_player.played == False or i < len(game.players) - 1:
        if len(cur_player.hand) < 1:
            cur_player.played = True
            i += 1
            continue
        # ! again Validation of inputs (suit, index, n)
        print(f"\n\nTeam {player._get_team(game)} sets:\n {game.team1_sets}")
        print(f"\n{cur_player.name} needs to remove {len(cur_player.hand)} cards.")
        suit_to_remove = input(f"\n{cur_player.name} which suit to remove? (c,d,h,s): ")
        if suit_to_remove not in ["c", "d", "h", "s"]:
            print("No suit selected. Try again.")
            break
        suit_to_remove = cur_player.get_suit(suit_to_remove)
        index_of_set = input(
            f"\nWhich set? from 0 to {len(game.team1_sets[suit_to_remove])-1}: "
        )
        if index_of_set.isdigit() == False or int(index_of_set) > len(
            game.team1_sets[suit_to_remove] - 1
        ):
            print("Invalid input, must be a valid number. Try again.")
            break

        n = input(f"\nHow many cards to remove from this set?): ")
        if (
            n.isdigit() == False
            or n > len(game.team1_sets[suit_to_remove] - 1)
            or n > len(cur_player.hand)
        ):
            print("must be a number up to the cards in your hand or set. Try again.")
            break

        # ! remove cards from set and hand
        cur_player.remove_from_set(n, suit_to_remove, index_of_set, game)
        if len(cur_player.hand) < 1:
            cur_player.played = True
            i += 1
            break
        else:
            # ! keep removing cards from hand until all cards are removed
            continue
    all_players_removed = True

# // Second, let's sum up the points for each team
team1_points = 0
team2_points = 0

n_cards = 0
for suit in game.team1_sets:
    for s in game.team1_sets[suit]:
        team1_points += points_from_set(s)
        n_cards += len(s)

team1_points += n_cards * 10

n_cards = 0
for suit in game.team2_sets:
    for s in game.team2_sets[suit]:
        team2_points += points_from_set(s)
        n_cards += len(s)

team2_points += n_cards * 10

if team1_points > team2_points:
    print(f"\n\nTeam 1 wins with {team1_points} points!")
elif team2_points > team1_points:
    print(f"\n\neam 2 wins with {team2_points} points!")
else:
    print(f"\n\nTeam 1 and Team 2 are tied with {team1_points} points!")
