import unittest
import pdb
from deck import Card
from helpers import is_in_order, rank_to_number, is_clean, extends_set, points_for_set
from random import shuffle
from deck import Card
from colored import fore, back, style

color = f'{fore("green")}{style(1)}'
reset = f"{style(0)}"
hearts = "♥"
diamonds = "♦"
clubs = "♣"
spades = "♠"


class TestHelpers(unittest.TestCase):
    def test_rank_to_number(self):
        self.assertEqual(rank_to_number("Ace", False), 1)
        self.assertEqual(rank_to_number("Ace", True), 14)
        self.assertEqual(rank_to_number("Jack"), 11)
        self.assertEqual(rank_to_number("Queen"), 12)
        self.assertEqual(rank_to_number("King"), 13)
        self.assertEqual(rank_to_number(10), 10)

    def test_sorting_cards(self):
        print(f"{color}****  start of sorting_cards ****\n{reset}{reset}")
        # unordered list of cards
        cards = [
            Card(hearts, 4),
            Card(spades, 2),
            Card(diamonds, "Ace"),
            Card(clubs, 7),
            Card(hearts, "King"),
            Card(spades, 3),
            Card(diamonds, 10),
            Card(clubs, "Queen"),
            Card(hearts, 6),
            Card(spades, 9),
            Card(diamonds, 5),
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

        print(f"test OK : sorted_cards")

    def test_is_in_order(self):
        print(f"{color}**** start of is_in_order tests ****\n{reset}{reset}")
        # Test with a simple sequence
        cards = [Card(hearts, rank) for rank in range(3, 6)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : a simple sequence 3,4,5\n")

        # Test with a sequence containing a joker
        cards = [Card(hearts, 2), Card(hearts, 4), Card(hearts, 5)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : joker front: 2,4,5\n")

        # Test with a sequence containing an Ace and a joker
        cards = [
            Card(hearts, "Ace"),
            Card(hearts, 2),
            Card(hearts, 3),
            Card(hearts, 4),
        ]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK : Ace low joker as 2: Ace,2,3,4\n")

        # Test with a sequence containing a joker in the middle
        cards = [Card(hearts, 4), Card(hearts, 2), Card(hearts, 6)]
        self.assertTrue(is_in_order(cards))
        print(f"tested OK :joker in the middle: 4,2,6\n")

        # Test with a sequence containing a Queen, a joker, and an Ace
        cards = [Card(hearts, "Queen"), Card(hearts, 2), Card(hearts, "Ace")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : Ace high joker in the middle: Q,2,A \n")

        # Test with a sequence containing a King, a joker, and an Ace
        cards = [Card(hearts, "King"), Card(hearts, 2), Card(hearts, "Ace")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : Ace high joker beginning: 2, K, A\n")

        # Test with a sequence containing 2, J, and K
        cards = [Card(hearts, 2), Card(hearts, "Jack"), Card(hearts, "King")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : no Ace figures and joker: 2,J,K\n")

        # Test with a sequence with Ace high until King
        cards = [
            Card(hearts, "Ace"),
            Card(hearts, "Jack"),
            Card(hearts, "Queen"),
            Card(hearts, "King"),
        ]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : Ace High clean: J,Q,K,A\n")

        # Test with a sequence containing 9, 2, and J
        cards = [Card(hearts, 9), Card(hearts, 2), Card(hearts, "Jack")]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : joker middle, number and figure: 9,2,J\n")

        # Test with a sequence containing 2,3,5,6
        cards = [
            Card(hearts, 2),
            Card(hearts, 3),
            Card(hearts, 5),
            Card(hearts, 6),
        ]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : clean with 2: 2,3,5,6\n")

        # Test with a sequence containing 3,5,2,7,8
        cards = [
            Card(hearts, 3),
            Card(hearts, 5),
            Card(hearts, 2),
            Card(hearts, 7),
            Card(hearts, 8),
        ]
        sorted_cards = sorted(cards)
        self.assertTrue(is_in_order(sorted_cards))
        print(f"tested OK : not clean order with 2: 3,5,2,7,8\n")

    def test_is_clean(self):
        print(f"{color}****  start of is_clean tests ****\n{reset}")
        # Test case 1: 3,4,5,6,7,8 - False
        cards1 = [Card(hearts, rank) for rank in range(3, 9)]
        self.assertFalse(is_clean(cards1))
        print(f"tested OK : not 7 cards in length\n")
        # Test case 2: 3,4,5,6,2,8,9 - False
        cards2 = [Card(hearts, rank) for rank in [3, 4, 5, 6, 2, 8, 9]]
        self.assertFalse(is_clean(cards2))
        print(f"tested OK : 2 in the middle\n")
        # Test case 3: 2,3,4,5,6,7,8 - True
        cards3 = [Card(hearts, rank) for rank in range(2, 9)]
        self.assertTrue(is_clean(cards3))
        print(f"tested OK : 2 in the beginning and length 7\n")
        # Test case 4: A,2,3,4,5,6 - False
        cards4 = [Card(hearts, rank) for rank in ["Ace", 2, 3, 4, 5, 6]]
        self.assertFalse(is_clean(cards4))
        print(f"tested OK : length 6 with 2 and Ace\n")
        # Test case 5: A,2,3,4,5,6,7 - True
        cards5 = [Card(hearts, rank) for rank in ["Ace", 2, 3, 4, 5, 6, 7]]
        self.assertTrue(is_clean(cards5))
        print(f"tested OK : length 7 with 2 and Ace front\n")
        # Test case 6: 8,9,10,"Jack","Queen","King","Ace" - True
        cards6 = [
            Card(hearts, rank) for rank in [8, 9, 10, "Jack", "Queen", "King", "Ace"]
        ]
        self.assertTrue(is_clean(cards6))
        print(f"tested OK : from 8 to high Ace\n")
        # Test case 7: 8,9,10,"Jack", "Queen", "King" - False
        cards7 = [Card(hearts, rank) for rank in [8, 9, 10, "Jack", "Queen", "King"]]
        self.assertFalse(is_clean(cards7))
        print(f"tested OK : from 8 to King\n")
        # Test case 8: 4,5,6,7,8,9,10 - True
        cards8 = [Card(hearts, rank) for rank in range(4, 11)]
        self.assertTrue(is_clean(cards8))
        print(f"tested OK : from 4 to 10\n")
        # Test case 9: 2,3,4,5,6,7,2 - False
        cards9 = [
            Card(hearts, rank)
            for rank in [
                2,
                3,
                4,
                5,
                6,
                7,
            ]
        ]
        cards9.append(Card(spades, 2))
        self.assertFalse(is_clean(cards9))
        print(f"tested OK : more than 1 two\n")

    def test_extends(self):
        print(f"{color}**** start of extends_set tests ****\n{reset}")
        chosen_set = [
            Card(rank=2, suit=hearts),
            Card(rank=3, suit=hearts),
            Card(rank=4, suit=hearts),
        ]
        card_list = [Card(rank=5, suit=hearts)]
        self.assertTrue(extends_set(chosen_set, card_list))
        print(f"tested OK : 5 extends_set 2,3,4\n")

        chosen_set = [
            Card(rank=2, suit=hearts),
            Card(rank=3, suit=hearts),
            Card(rank=4, suit=hearts),
        ]
        card_list = [
            Card(rank=2, suit=hearts),
            Card(rank=5, suit=hearts),
            Card(rank=6, suit=hearts),
        ]
        self.assertFalse(extends_set(chosen_set, card_list))
        print(f"test OK : 2 jokers same suit\n")

        chosen_set = [
            Card(rank=2, suit=hearts),
            Card(rank=3, suit=hearts),
            Card(rank=4, suit=hearts),
        ]
        card_list = [
            Card(rank=2, suit=spades),
            Card(rank=6, suit=hearts),
            Card(rank=7, suit=hearts),
        ]
        self.assertTrue(extends_set(chosen_set, card_list))
        print(f"test OK : 2 jokers different suit\n")

        chosen_set = [
            Card(rank=2, suit=hearts),
            Card(rank=3, suit=hearts),
            Card(rank=4, suit=hearts),
        ]
        card_list = [
            Card(rank=2, suit=spades),
            Card(rank=2, suit=hearts),
            Card(rank=7, suit=hearts),
        ]
        self.assertFalse(extends_set(chosen_set, card_list))
        print(f"test OK : 3 jokers ?? \n")

        chosen_set = [
            Card(rank=2, suit=hearts),
            Card(rank=3, suit=hearts),
            Card(rank=4, suit=hearts),
        ]
        card_list = [
            Card(rank="Ace", suit=hearts),
            Card(rank=5, suit=hearts),
        ]
        self.assertTrue(extends_set(chosen_set, card_list))
        print(f"test OK : extends_set both sides A,5 - 2,3,4\n")

        chosen_set = [Card(hearts, rank) for rank in range(2, 11)]
        add = [Card(hearts, "Jack"), Card(hearts, "Queen"), Card(hearts, "King")]
        chosen_set.extend(add)

        chosen_set = sorted(chosen_set)
        card_list = [
            Card(rank="Ace", suit=hearts),
            Card(rank="Ace", suit=hearts),
        ]
        self.assertTrue(extends_set(chosen_set, card_list))
        print(f"test OK : extends_set Ace high and Low 1000pts!\n")

    def test_points_from_set(self):
        print(f"{color}**** start of points_for_set tests ****\n{reset}")
        # Test case 1: 3,4,5,6,7,8 - 0 points
        cards1 = [Card(hearts, rank) for rank in range(3, 9)]
        self.assertEqual(points_for_set(cards1), 0)
        print(f"tested OK : 0 points for 3,4,5,6,7,8\n")

        # Test case 2: 3,4,5,6,2,8,9 - 100 points
        cards2 = [Card(hearts, rank) for rank in [3, 4, 5, 6, 2, 8, 9]]
        self.assertEqual(points_for_set(cards2), 100)
        print(f"tested OK : 100 points for 3,4,5,6,2,8,9\n")

        # Test case 3: 2,3,4,5,6,7,8 - 200 points
        cards3 = [Card(hearts, rank) for rank in range(2, 9)]
        self.assertEqual(points_for_set(cards3), 200)
        print(f"tested OK : 200 points for 2,3,4,5,6,7,8\n")

        # Test case 4: A,2,3,4,5,6,7,8,9,10,Jack,Queen,King - 500 points
        cards4 = [Card(hearts, rank) for rank in range(2, 11)]
        add = [
            Card(hearts, "Jack"),
            Card(hearts, "Queen"),
            Card(hearts, "King"),
            Card(hearts, "Ace"),
        ]
        cards4.extend(add)
        cards4 = sorted(cards4)
        self.assertEqual(points_for_set(cards4), 500)
        print(f"tested OK : 500 points for A --> King\n")

        # test case 5: A --> A - 1000 points
        cards5 = [Card(hearts, rank) for rank in range(2, 11)]
        add = [
            Card(hearts, "Jack"),
            Card(hearts, "Queen"),
            Card(hearts, "King"),
            Card(hearts, "Ace"),
            Card(hearts, "Ace"),
        ]
        cards5.extend(add)
        cards5 = sorted(cards5)
        self.assertEqual(points_for_set(cards5), 1000)
        print(f"tested OK : 1000 points for A --> A\n")


if __name__ == "__main__":
    unittest.main()
