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
        self.hand.append(card)

    def discard(self, card):
        rank, suit = card.split(",")[0], card.split(",")[1].lower()
        suits = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}
        if suit in suits:
            suit = suits[suit]

        card = self.get_card(rank, suit)
        self.hand.remove(card)

    def drop_set(self, card_list, suit, game):
        team_set = game._get_team_set(self)
        if new_set == None or new_set in team_set[suit]:
            raise ValueError("You must choose a set to drop the cards.")
        new_set = card_list

    def extend_set(self, card_list, set_to_add, game):
        s = set_to_add
        # ! CARD_LIST must be SORTED BY RANK [(1,H),(2,H),(3,H)]
        if s._extends(sorted(card_list)):
            print(f"Adding {card_list} to {s}")
            s._add_to_set(card_list)
        else:
            raise ValueError("Cards do not extend the chosen set.")

    def get_card(self, rank, suit):
        if rank.isdigit():
            rank = int(rank)

        for card in self.hand:
            if card.rank == rank and card.suit == suit:
                return card
        return None

    def get_trash(self, trash):
        self.hand.append(t for t in trash)

    def get_new_hand(self, hand):
        self.hand = hand

    def organize_hand(self):
        # TODO: sort by suit and rank when called
        return sorted(self.hand)

    def _is_play_valid(self, cards):
        """
        // check if all cards are in hand
        // have the same suit or card.rank == 2
        """
        for card in cards:
            rank, suit = card.split(",")[0], card.split(",")[1].lower()
            suits = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}
            if suit in suits:
                suit = suits[suit]

            c = self.get_card(rank, suit)

            if c not in self.hand:
                print("Card not in hand.")
                return False
            if c.suit != suit:
                if c.rank == 2:
                    continue
                else:
                    print("A set of Cards must be of the same suit. Try again.")
                    return False
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
