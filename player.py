class Player:
    def __init__(self, number, name, hand):
        self.name = name
        self.number = number
        self.hand = hand

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Player {self.number}-{self.name}\n cards in hand: {self.hand}\n"

    def draw(self, deck):
        card = deck.deal()
        self.hand.append(card)

    def discard(self, card):
        return self.hand.remove(card)

    def drop(self, card_list):
        cards_to_drop = []
        for card in card_list:
            cards_to_drop.append(self.hand.pop(index(card)))

    def get_trash(self, trash):
        self.hand.append(t for t in trash)

    def get_new_hand(self, hand):
        self.hand = hand

    def organize_hand(self):
        for card in self.hand:
            print(card)
