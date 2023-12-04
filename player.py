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

    def get_trash(self, trash):
        self.hand.append(t for t in trash)

    def get_new_hand(self, hand):
        self.hand = hand

    def organize_hand(self):
        for card in self.hand:
            print(card)

    def _is_play_valid(self, cards):
        """
        // check if all cards are in hand
        // have the same suit or card.rank == 2
        """

        suit = cards[0].suit
        for card in cards:
            if card not in self.hand:
                print("Card not in hand.")
                return False
            if card.suit != suit:
                if card.rank == 2:
                    continue
                else:
                    print("A set of Cards must be of the same suit. Try again.")
                    return False
        return True
