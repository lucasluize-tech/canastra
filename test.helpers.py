import unittest
import pdb
from deck import Card
from helpers import is_in_order, rank_to_number, is_clean
from random import shuffle
from deck import Card


class TestHelpers(unittest.TestCase):
    def test_rank_to_number(self):
        self.assertEqual(rank_to_number("Ace", False), 1)
        self.assertEqual(rank_to_number("Ace", True), 14)
        self.assertEqual(rank_to_number("Jack"), 11)
        self.assertEqual(rank_to_number("Queen"), 12)
        self.assertEqual(rank_to_number("King"), 13)
        self.assertEqual(rank_to_number(10), 10)

    def test_sorting_cards(self):
        # unordered list of cards
        cards = [
            Card("Hearts", 4),
            Card("Spades", 2),
            Card("Diamonds", "Ace"),
            Card("Clubs", 7),
            Card("Hearts", "King"),
            Card("Spades", 3),
            Card("Diamonds", 10),
            Card("Clubs", "Queen"),
            Card("Hearts", 6),
            Card("Spades", 9),
            Card("Diamonds", 5),
        ]

        sorted_cards = sorted(cards)
        self.assertEqual(sorted_cards[0].rank, 7)
        self.assertEqual(sorted_cards[1].rank, "Queen")
        self.assertEqual(sorted_cards[2].rank, "Ace")
        self.assertEqual(sorted_cards[3].rank, 5)
        self.assertEqual(sorted_cards[4].rank, 10)
        self.assertEqual(sorted_cards[5].rank, 4)
        self.assertEqual(sorted_cards[6].rank, 6)
        self.assertEqual(sorted_cards[7].rank, "King")
        self.assertEqual(sorted_cards[8].rank, 2)
        self.assertEqual(sorted_cards[9].rank, 3)
        self.assertEqual(sorted_cards[10].rank, 9)

        print(f"sorted_cards: TRUE")

    def test_is_in_order(self):
        # Test with a simple sequence
        cards = [Card("Hearts", rank) for rank in range(3, 6)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : a simple sequence 3,4,5\n")

        # Test with a sequence containing a joker
        cards = [Card("Hearts", 2), Card("Hearts", 4), Card("Hearts", 5)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : a sequence containing a joker 2,4,5\n")

        # Test with a sequence containing an Ace and a joker
        cards = [Card("Hearts", "Ace"), Card("Hearts", 2), Card("Hearts", 3)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : a sequence containing an Ace and a joker Ace,2,3\n")

        # Test with a sequence containing a joker in the middle
        cards = [Card("Hearts", 4), Card("Hearts", 2), Card("Hearts", 6)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : a sequence containing a joker in the middle 4,2,6\n")

        # Test with a sequence containing a Queen, a joker, and an Ace
        cards = [Card("Hearts", "Queen"), Card("Hearts", 2), Card("Hearts", "Ace")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing a Queen, a joker, and an Ace \n")

        # Test with a sequence containing a King, a joker, and an Ace
        cards = [Card("Hearts", "King"), Card("Hearts", 2), Card("Hearts", "Ace")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing a King, a joker, and an Ace\n")

        # Test with a sequence containing 2, J, and K
        cards = [Card("Hearts", 2), Card("Hearts", "Jack"), Card("Hearts", "King")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing 2, J, and K\n")

        # Test with a sequence containing 9, 2, and J
        cards = [Card("Hearts", 9), Card("Hearts", 2), Card("Hearts", "Jack")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing 9, 2, and J\n")

        # Test with a sequence containing 2,3,5,6
        cards = [
            Card("Hearts", 2),
            Card("Hearts", 3),
            Card("Hearts", 5),
            Card("Hearts", 6),
        ]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing 2,3,5,6\n")

        # Test with a sequence containing 3,5,2,7,8
        cards = [
            Card("Hearts", 3),
            Card("Hearts", 5),
            Card("Hearts", 2),
            Card("Hearts", 7),
            Card("Hearts", 8),
        ]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : a sequence containing 3,5,2,7,8\n")

    def test_is_clean(self):
        # Test case 1: 3,4,5,6,7,8 - False
        cards1 = [Card("Hearts", rank) for rank in range(3, 9)]
        self.assertFalse(is_clean(cards1))
        print(f"tested OK : not 7 cards in length\n")
        # Test case 2: 3,4,5,6,2,8 - False
        cards2 = [Card("Hearts", rank) for rank in [3, 4, 5, 6, 2, 8]]
        self.assertFalse(is_clean(cards2))
        print(f"tested OK : 2 in the middle\n")
        # Test case 3: 2,3,4,5,6,7,8 - True
        cards3 = [Card("Hearts", rank) for rank in range(2, 9)]
        self.assertTrue(is_clean(cards3))
        print(f"tested OK : 2 in the beginning and length 7\n")
        # Test case 4: A,2,3,4,5,6 - False
        cards4 = [Card("Hearts", rank) for rank in ["Ace", 2, 3, 4, 5, 6]]
        self.assertFalse(is_clean(cards4))
        print(f"tested OK : length 6 with 2 and Ace\n")
        # Test case 5: A,2,3,4,5,6,7 - True
        cards5 = [Card("Hearts", rank) for rank in ["Ace", 2, 3, 4, 5, 6, 7]]
        self.assertTrue(is_clean(cards5))
        print(f"tested OK : length 7 with 2 and Ace front\n")
        # Test case 6: 8,9,10,"Jack","Queen","King","Ace" - True
        cards6 = [
            Card("Hearts", rank) for rank in [8, 9, 10, "Jack", "Queen", "King", "Ace"]
        ]
        self.assertTrue(is_clean(cards6))
        print(f"tested OK : from 8 to high Ace\n")
        # Test case 7: 8,9,10,"Jack", "Queen", "King" - False
        cards7 = [Card("Hearts", rank) for rank in [8, 9, 10, "Jack", "Queen", "King"]]
        self.assertFalse(is_clean(cards7))
        print(f"tested OK : from 8 to King\n")
        # Test case 8: 4,5,6,7,8,9,10 - True
        cards8 = [Card("Hearts", rank) for rank in range(4, 11)]
        self.assertTrue(is_clean(cards8))
        print(f"tested OK : from 4 to 10\n")
        # Test case 9: 2,3,4,5,6,7,2 - False
        cards9 = [
            Card("Hearts", rank)
            for rank in [
                2,
                3,
                4,
                5,
                6,
                7,
            ]
        ]
        cards9.append(Card("Spades", 2))
        self.assertFalse(is_clean(cards9))
        print(f"tested OK : more than 1 two\n")


if __name__ == "__main__":
    unittest.main()
