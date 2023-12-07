import random


class Deck:
    def __init__(self, n=1):
        self.cards = []
        self._add_all_cards(n)

    def _add_all_cards(self, n):
        suits = ["Clubs", "Diamonds", "Hearts", "Spades"]
        i = n
        while i > 0:
            for suit in suits:
                for rank in range(1, 14):
                    if rank == 11:
                        rank = "Jack"
                    elif rank == 12:
                        rank = "Queen"
                    elif rank == 13:
                        rank = "King"
                    elif rank == 1:
                        rank = "Ace"
                    self.cards.append(Card(suit, rank))
            i -= 1

    def _shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        return self.cards.pop()

    def _deal_new_hands(self, n):
        result = []
        # randomly select 11 cards from the deck
        for _ in range(n):
            hand = []
            result.append(hand)
            i = 0
            while i < 11:
                card = self.deal()
                hand.append(card)
                i += 1

        return result

    def __repr__(self):
        return str(self.cards)


class Card:
    rank_order = {
        "Ace": 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        6: 6,
        7: 7,
        8: 8,
        9: 9,
        10: 10,
        "Jack": 11,
        "Queen": 12,
        "King": 13,
    }
    suit_order = {"Clubs": 1, "Diamonds": 2, "Hearts": 3, "Spades": 4}

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"({self.rank},{self.suit[0].capitalize()})"

    def __repr__(self):
        return f"({self.rank},{self.suit[0].capitalize()})"

    def _cmp_key(self):
        return (self.suit_order[self.suit], self.rank_order[self.rank])

    def __lt__(self, other):
        return self._cmp_key() < other._cmp_key()

    def __gt__(self, other):
        return self._cmp_key() > other._cmp_key()

    def __eq__(self, other):
        return self._cmp_key() == other._cmp_key()
