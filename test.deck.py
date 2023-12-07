import unittest
from deck import Deck, Card
from player import Player
from table import Table


class Test(unittest.TestCase):
    suits = ["Clubs", "Diamonds", "Hearts", "Spades"]
    names = ["Julio", "Rafael", "Ricardo", "Rafaela"]
    NUMBER_OF_PLAYERS = 4
    NUMBER_OF_DECKS = 4
    NUMBER_OF_NEW_HANDS = 4

    def test_deck_creation(self):
        # ! testing number of cards , and if all cards are instances of Card
        n_cards = 52 * self.NUMBER_OF_DECKS
        deck = Deck(self.NUMBER_OF_DECKS)  # 2 decks

        self.assertEqual(len(deck.cards), n_cards)

        for card in deck.cards:
            self.assertIsInstance(card, Card)

        print(f"tested OK : right length and all cards are instances of Card\n")

    def test_shuffle(self):
        # ! testing if the first and last cards are different after shuffling
        deck = Deck(self.NUMBER_OF_DECKS)
        first, last = deck.cards[0], deck.cards[-1]
        shuffled = deck._shuffle()
        new_first, new_last = deck.cards[0], deck.cards[-1]

        self.assertNotEqual(first, new_first)
        self.assertNotEqual(last, new_last)

        print(f"tested OK : first and last cards are different after shuffling\n")

    def test_new_hands_creation(self):
        # ! testing # of new hands and if those cards are not in the deck
        deck = Deck(self.NUMBER_OF_DECKS)
        new_hands = [hand for hand in deck._deal_new_hands(self.NUMBER_OF_DECKS)]
        players = [
            Player(self.names[i], new_hands[i]) for i in range(self.NUMBER_OF_PLAYERS)
        ]
        game = Table(players, deck, new_hands[self.NUMBER_OF_PLAYERS :])

        self.assertEqual(len(new_hands), self.NUMBER_OF_NEW_HANDS)
        self.assertTrue(len(deck.cards) == (52 * self.NUMBER_OF_DECKS) - 4 * 11)
        print(f"tested OK : # of new hands and if those cards are not in the deck\n")


if __name__ == "__main__":
    unittest.main()
