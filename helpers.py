# ! ALL COMMENT FOLLOWED BY ! IN THIS FILE ARE FOR TESTING PURPOSES ONLY
"""
// This file contains helper functions for the canastra game
// is_in_order: checks if a list of cards is in sequential order
// rank_to_number: converts a card's rank to a number(Ace can be 1 or 14)
// extends: checks if a set of cards can be extended with a list of cards
// is_clean: checks if a list of cards is a clean canastra
// points_for_set: calculates the points for a set of cards
"""


def is_in_order(cards):
    # Get the first and last cards in the list
    cards = sorted(cards)
    first, last = cards[0], cards[-1]
    # ! print(cards)
    # Check if the first card is an Ace and the last card is a King or a joker
    high_ace = first.rank == "Ace" and (last.rank == "King" or last.rank == "Queen")

    # Loop through the list of cards, starting from the second card
    for i in range(1, len(cards) - 1):
        # Convert the current card's rank to a number
        current_rank = rank_to_number(cards[i].rank, high_ace)

        # Convert the previous card's rank to a number
        previous_rank = rank_to_number(cards[i - 1].rank, high_ace)

        # Convert the next card's rank to a number
        next_rank = rank_to_number(cards[i + 1].rank, high_ace)
        # ! print(
        # !    f"cur : {current_rank} , prev : {previous_rank}, next:{next_rank}, high_ace: {high_ace}")
        # Check if the current card is a joker
        if current_rank == 2:
            # If the next card's rank is not two more than the previous card's rank, return False

            if high_ace is True and last.rank == "Queen":
                if next_rank != previous_rank - 2:
                    return False
            elif high_ace is True and last.rank == "King":
                if next_rank != previous_rank - 1:
                    return False
            else:
                if next_rank != previous_rank + 2:
                    return False

        # Check if the previous card was a joker
        elif previous_rank == 2:
            # If the next card's rank is not one or two more than the current card's rank, return False
            if current_rank + 1 == next_rank or current_rank + 2 == next_rank:
                continue
            else:
                return False

        # Check if the current card's rank is not one more than the previous card's rank
        else:
            # lets say A,10,j,Q,K
            if previous_rank == 14:
                if current_rank + 1 != next_rank:
                    return False
            elif current_rank != previous_rank + 1 and first.rank != 2:
                return False

    # If all checks pass, return True
    return True


def rank_to_number(rank, high_ace=False):
    if rank == "Ace":
        return 14 if high_ace else 1
    elif rank == "Jack":
        return 11
    elif rank == "Queen":
        return 12
    elif rank == "King":
        return 13
    else:
        return rank


def extends_set(chosen_set, card_list):
    """
    // extends if :
    // only a sigle "2" of the same suit is allowed per set
    // new cards must not be in the set
    // cannot have two cards of the same rank in the set
    """
    num_of_twos = len([card for card in chosen_set if card.rank == 2])
    # ! print(
    #     f"num_of_twos: {num_of_twos}, chosen_set: {chosen_set}, card_list: {card_list}"
    # )

    for s in chosen_set:
        # ! print(f"s: {s.rank}, prev: {prev}")
        suit = chosen_set[-1].suit
        if s.rank == "Ace" and prev == 1:
            continue

        for card in card_list:
            # !print(f"card: {card.rank}, suit: {suit}")
            if card.rank == s.rank and card.rank != 2:
                return False
            if card.rank == 2 and card.suit == suit:
                return False
        prev = rank_to_number(card.rank)

    if num_of_twos > 2:
        return False

    return True


def is_clean(card_list):
    if len(card_list) < 7:
        return False

    card_list = sorted(card_list)
    # !print(f"\ncard_list: {card_list}")
    first, last = card_list[0], card_list[-1]
    num_of_twos = len([card for card in card_list if card.rank == 2])
    high_ace = True if last.rank == "King" else False
    # !print(
    # !    f"first rank: {first.rank}, last rank: {last.rank}, high_ace: {high_ace}, num_of_twos: {num_of_twos}, length: {len(card_list)}")
    for i in range(1, len(card_list) - 1):
        """
        For a canastra to be clean ,"2" must be in the twos place. max 1
        * possible clean canastra: 2,3,4,5,6,7,8...
        * possible clean canastra: A,2,3,4,5,6,7...
        * possible clean canastra: 7,8,9,10,J,Q,K ...
        """
        cur = rank_to_number(card_list[i].rank, high_ace)
        prev = rank_to_number(card_list[i - 1].rank, high_ace)
        Next = rank_to_number(card_list[i + 1].rank, high_ace)
        # ! print(f"cur: {cur}, prev: {prev}, Next: {Next}")

        if num_of_twos > 1:
            return False
        if cur == 2 and prev != 1 and Next != 3:
            return False
        else:
            if prev != cur - 1 or Next != cur + 1:
                if prev == 14:
                    continue
                return False

    return True


def points_for_set(s):
    """
    * clen from A->A: 1000
    * clean from A->K: 500
    * clean canastra: 200
    * dirty canastra: 100
    * cards on the table: 10/each but this will be handled on the main file
    """
    points = 0
    first, second, last = s[0], s[1], s[-1]

    if first.rank == "Ace" and second.rank == "Ace" and len(s) == 14:
        points += 1000

    elif first.rank == "Ace" and last.rank == "King" and len(s) == 13:
        points += 500

    elif is_clean(s) == True:
        points += 200

    elif is_clean(s) == False and len(s) >= 7:
        points += 100
    else:
        return points
    return points
