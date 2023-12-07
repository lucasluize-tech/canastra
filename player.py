from deck import Card
from helpers import is_in_order, extends


class Player:
    def __init__(self, name, hand):
        self.name = name
        self.hand = hand
        self.played = False

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Player {self.name}\n cards in hand: {self.hand}\n"

    def _get_team(self, game):
        if self in game.team1:
            return "1"
        else:
            return "2"

    def draw(self, deck):
        card = deck.deal()
        print(f"\nYou drew {card} from the deck.\n")
        self.hand.append(card)

    def discard(self, card):
        self.hand.remove(card)
        return card

    def drop_set(self, card_list, suit, game):
        team_set = game._get_team_set(self)
        card_list = sorted(card_list)
        if team_set.get(suit) is None:
            team_set[suit] = [(card_list)]
            print(f"team set now is : {team_set}")
        else:
            team_set[suit].append(card_list)
            print(f"team set now is : {team_set}")
        for card in card_list:
            self.hand.remove(card)

    def can_extend_set(self, card_list, index, game):
        team_set = game._get_team_set(self)[index]
        if extends(team_set, card_list) is True:
            print(f"Adding {card_list} to {team_set}")
            team_set.append(card_list)
            team_set = sorted(team_set)
            return True
        else:
            print("\nCards do not extend the chosen set.")
            return False

    def get_rank_and_suit(self, card):
        if card is None:
            raise ValueError("No cards selected.")
        rank, suit = card.split(",")[0], card.split(",")[1].lower()
        suits = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}
        suit = suits[suit]
        new_card = self.get_card(rank, suit)

        return new_card

    def get_card(self, index):
        self.hand = sorted(self.hand)
        i = int(index) - 1
        card = self.hand[i]
        return card

    def get_trash(self, trash):
        for card in trash:
            self.hand.append(card)

    def get_new_hand(self, hand):
        self.hand = hand

    def organize_hand(self):
        return sorted(self.hand)

    def _is_play_valid(self, cards):
        """
        * cards must: be in hand
        * have the same suit or card.rank == 2
        * only two twos allowed per set if FOREVER DIRTY
        * set must be n , n.rank +1, n.rank+2 if (len(n) == 3) and so on
        """
        cur_card = cards[0]
        num_of_twos = 0

        # // 1. have the same suit or card.rank == 2
        for card in cards:
            if card not in self.hand:
                print("Cards must be in hand. Try again.")
                return False
            if card.suit != cur_card.suit:
                if card.rank != 2:
                    print("Cards must be of the same suit. Try again.")
                    return False
                else:
                    # // 2. only two twos allowed per set 'FOREVER DIRTY'
                    num_of_twos += 1
                    if num_of_twos > 2:
                        print("Only two twos allowed per set. Try again.")
                        return False

        # // 3. set must be n , n.rank +1, n.rank+2 if (len(n) == 3) and so on
        if len(cards) > 2:
            in_order = is_in_order(cards)
            if in_order == False:
                print("Cards must be in sequential order. Try again.")
                return False
            pass

        return True

    def chin(self, game):
        team = self._get_team(game)
        if team == "1":
            if game.team1_hands == 2 and game._team_has_clean_canastra(self):
                print(f"Game over! Team 1 finished the game!")
                return True
            else:
                game.team1_hands += 1
                self.get_new_hand(game.new_hands.pop())
                return False
        else:
            if game.team2_hands == 2 and game._team_has_clean_canastra(self):
                print(f"Game over! Team 2 finished the game!")
                return True
            else:
                game.team2_hands += 1
                self.get_new_hand(game.new_hands.pop())
                return False

    def is_over_or_new_hands(self, game):
        if len(self.hand) == 0:
            # chin also gets new hand if needed
            chin = self.chin(game)
            if chin == True:
                return True
            print(f" {self.name} needs got a new hand.")
            return False
