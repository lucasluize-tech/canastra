"""Set-level scoring.

Phase 1 port. ``points_for_set`` returns the canastra bonus:

  * 1000 — 14-card Ace-low + Ace-high run
  * 500  — 13-card 2…King + Ace run
  * 200  — clean canastra (≥ 7, no wilds)
  * 100  — dirty canastra (≥ 7, any wilds including permanent-dirty)
  * 0    — short sets (table-card bonus of 10/card is computed elsewhere)

``points_from_set`` is a legacy alias — ``main.py`` calls the misspelled
name; the alias keeps the terminal game running until Phase 3 tidies the
call sites.
"""

from __future__ import annotations

from canastra.domain.cards import Card
from canastra.domain.rules import is_clean


def points_for_set(s: list[Card]) -> int:
    if len(s) < 7:
        return 0

    first, second, last = s[0], s[1], s[-1]

    if first.rank == "Ace" and second.rank == "Ace" and len(s) == 14:
        return 1000
    if first.rank == "Ace" and last.rank == "King" and len(s) == 13:
        return 500
    if is_clean(s):
        return 200
    return 100


def points_from_set(s: list[Card]) -> int:
    """Legacy alias. See module docstring."""
    return points_for_set(s)
