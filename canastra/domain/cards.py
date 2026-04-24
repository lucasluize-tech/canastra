"""Cards and decks.

Pure, deterministic, side-effect-free. Shuffling accepts an injectable
``random.Random`` so tests can seed it; the old behavior (shuffle with the
module-level RNG) is preserved when no RNG is passed.

Exports: ``Card``, ``Deck``, ``Suit`` (the four unicode glyph constants).

Rank is intentionally polymorphic (``str`` for face cards and Ace, ``int``
for 2..10). This matches the legacy terminal code and its test fixtures —
do not normalize without updating every call site in one pass.
"""

from __future__ import annotations

import random
from typing import Any

Suit = str  # one of "♥", "♦", "♣", "♠"
Rank = Any  # "Ace" | 2..10 | "Jack" | "Queen" | "King" — mixed by design

HEARTS: Suit = "♥"
DIAMONDS: Suit = "♦"
CLUBS: Suit = "♣"
SPADES: Suit = "♠"

SUITS: tuple[Suit, ...] = (CLUBS, DIAMONDS, HEARTS, SPADES)

_SHORT_RANK: dict[Any, str] = {
    "Ace": "A",
    "Jack": "J",
    "Queen": "Q",
    "King": "K",
}


def _short(rank: Any) -> str:
    return _SHORT_RANK.get(rank, str(rank))


class Card:
    rank_order: dict[Any, int] = {
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
    suit_order: dict[Suit, int] = {CLUBS: 1, DIAMONDS: 2, HEARTS: 3, SPADES: 4}

    def __init__(self, suit: Suit, rank: Rank) -> None:
        self.suit = suit
        self.rank = rank

    def __str__(self) -> str:
        return f"{_short(self.rank)}{self.suit}"

    def __repr__(self) -> str:
        return f"{_short(self.rank)}{self.suit}"

    def _cmp_key(self) -> tuple[int, int]:
        return (self.suit_order[self.suit], self.rank_order[self.rank])

    def __lt__(self, other: Card) -> bool:
        return self._cmp_key() < other._cmp_key()

    def __gt__(self, other: Card) -> bool:
        return self._cmp_key() > other._cmp_key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self._cmp_key() == other._cmp_key()

    def __hash__(self) -> int:
        return hash(self._cmp_key())


class Deck:
    def __init__(self, n: int = 1) -> None:
        self.cards: list[Card] = []
        self._add_all_cards(n)

    def _add_all_cards(self, n: int) -> None:
        i = n
        while i > 0:
            for suit in SUITS:
                for raw in range(1, 14):
                    rank: Rank
                    if raw == 1:
                        rank = "Ace"
                    elif raw == 11:
                        rank = "Jack"
                    elif raw == 12:
                        rank = "Queen"
                    elif raw == 13:
                        rank = "King"
                    else:
                        rank = raw
                    self.cards.append(Card(suit, rank))
            i -= 1

    def _shuffle(self, rng: random.Random | None = None) -> None:
        if rng is None:
            random.shuffle(self.cards)
        else:
            rng.shuffle(self.cards)

    def deal(self) -> Card:
        return self.cards.pop()

    def _deal_new_hands(self, n: int) -> list[list[Card]]:
        result: list[list[Card]] = []
        for _ in range(n):
            hand: list[Card] = []
            result.append(hand)
            i = 0
            while i < 11:
                hand.append(self.deal())
                i += 1
        return result

    def __repr__(self) -> str:
        return str(self.cards)
