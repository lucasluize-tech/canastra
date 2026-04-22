"""Pure domain for Canastra.

Exports cards (`Card`, `Deck`, `Suit`), rules (run/clean/extend validation),
and scoring. No I/O, no randomness except via an injected RNG.

Rule reference: see the canonical rules memo (project_canastra_rules.md) —
this package's behavior is the executable version of that document.
"""

from canastra.domain.cards import Card, Deck, Suit
from canastra.domain.rules import (
    WILD_RANK,
    extends_set,
    is_clean,
    is_in_order,
    is_permanent_dirty,
    rank_to_number,
)
from canastra.domain.scoring import points_for_set, points_from_set

__all__ = [
    "WILD_RANK",
    "Card",
    "Deck",
    "Suit",
    "extends_set",
    "is_clean",
    "is_in_order",
    "is_permanent_dirty",
    "points_for_set",
    "points_from_set",
    "rank_to_number",
]
