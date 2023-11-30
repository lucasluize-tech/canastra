import unittest
from deck import Deck, Card


class Test(unittest.TestCase):
    suits = ["Clubs", "Diamonds", "Hearts", "Spades"]

    def test_deck_creation(self):
        n = 2
        n_cards = 52 * n
        deck = Deck(n)  # 2 decks

        self.assertEqual(len(deck.cards), n_cards)

        for card in deck.cards:
            self.assertIsInstance(card, Card)

    def test_new_hands_creation(self):
        n = 4 + 4  # !( 4 players + 4 new_hands )
        deck = Deck(n)

        new_hands = [hand for hand in deck._deal_new_hands(n)]
        self.assertTrue(len(new_hands) == n)
        self.assertTrue(len(deck.cards) == (52 * n / 2) - (11 * n))
        for i in range(4):
            new_total += len(deck.cards[self.suits[i]])
            self.assertTrue(len(new_hands[i]) == 13)
        self.assertTrue(new_total < total)


if __name__ == "__main__":
    unittest.main()
