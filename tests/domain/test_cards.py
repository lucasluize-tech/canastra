"""Deterministic + property-based tests for ``canastra.domain.cards``."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from canastra.domain.cards import (
    CLUBS,
    DIAMONDS,
    HEARTS,
    SPADES,
    SUITS,
    Card,
    Deck,
)

RANKS = ["Ace", 2, 3, 4, 5, 6, 7, 8, 9, 10, "Jack", "Queen", "King"]


suit_strategy = st.sampled_from(SUITS)
rank_strategy = st.sampled_from(RANKS)
card_strategy = st.builds(Card, suit_strategy, rank_strategy)


class TestDeck:
    def test_single_deck_has_52_cards(self) -> None:
        assert len(Deck().cards) == 52

    def test_n_decks_have_52n_cards(self) -> None:
        for n in (1, 2, 4, 6):
            assert len(Deck(n).cards) == 52 * n

    def test_deal_new_hands_pulls_11_each(self) -> None:
        d = Deck(4)
        start = len(d.cards)
        hands = d._deal_new_hands(3)
        assert len(hands) == 3
        assert all(len(h) == 11 for h in hands)
        assert len(d.cards) == start - 33


class TestCardEquality:
    def test_same_suit_rank_equal(self) -> None:
        assert Card(HEARTS, 5) == Card(HEARTS, 5)

    def test_different_deck_copies_still_equal(self) -> None:
        """``Card.__eq__`` ignores deck identity — intended for multi-deck play."""
        a, b = Card(CLUBS, "Ace"), Card(CLUBS, "Ace")
        assert a == b
        assert a is not b

    def test_different_rank_not_equal(self) -> None:
        assert Card(HEARTS, 5) != Card(HEARTS, 6)

    def test_different_suit_not_equal(self) -> None:
        assert Card(HEARTS, 5) != Card(SPADES, 5)

    def test_eq_with_non_card_returns_not_implemented(self) -> None:
        assert (Card(HEARTS, 5) == "not a card") is False


class TestCardHashing:
    def test_equal_cards_hash_equal(self) -> None:
        assert hash(Card(HEARTS, 5)) == hash(Card(HEARTS, 5))

    def test_card_usable_in_set(self) -> None:
        """Regression: ``__eq__`` without ``__hash__`` makes cards unhashable."""
        s = {Card(HEARTS, 5), Card(HEARTS, 5), Card(DIAMONDS, 5)}
        assert len(s) == 2

    def test_card_usable_as_dict_key(self) -> None:
        counts: dict[Card, int] = {}
        for c in (Card(HEARTS, 5), Card(HEARTS, 5), Card(SPADES, "Ace")):
            counts[c] = counts.get(c, 0) + 1
        assert counts[Card(HEARTS, 5)] == 2


class TestCardOrdering:
    def test_sorts_by_suit_then_rank(self) -> None:
        cards = [Card(SPADES, 3), Card(CLUBS, "King"), Card(CLUBS, "Ace")]
        assert sorted(cards) == [
            Card(CLUBS, "Ace"),
            Card(CLUBS, "King"),
            Card(SPADES, 3),
        ]

    @given(card_strategy, card_strategy)
    def test_ordering_is_antisymmetric(self, a: Card, b: Card) -> None:
        if a == b:
            assert not (a < b) and not (a > b)
        else:
            assert (a < b) != (a > b)
