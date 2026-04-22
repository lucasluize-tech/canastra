"""Set-level scoring.

``points_for_set`` returns the per-set canastra bonus:

  * 1000 - 14-card Ace-low + Ace-high run
  * 500  - 13-card run that contains exactly one Ace
  * 200  - clean canastra (>= 7 cards, no wild)
  * 100  - dirty canastra (>= 7 cards, contains a wild)
  * 0    - short sets (table-card bonus of 10 per card is scored elsewhere)

The 1000-point and 500-point tiers are detected by rank content
(``Ace`` count plus length), not by positional ``s[0]``/``s[1]`` checks,
so the caller does not need to pre-sort the list.

``points_from_set`` is a legacy alias - ``main.py`` calls the misspelled
name; the alias keeps the terminal game running until Phase 3 tidies the
call sites.
"""

from __future__ import annotations

from canastra.domain.cards import Card
from canastra.domain.rules import is_clean

_MIN_CANASTRA: int = 7


def points_for_set(s: list[Card]) -> int:
    length = len(s)
    if length < _MIN_CANASTRA:
        return 0

    ace_count = sum(1 for c in s if c.rank == "Ace")
    if length == 14 and ace_count == 2:
        return 1000
    if length == 13 and ace_count == 1:
        return 500
    if is_clean(s):
        return 200
    return 100


def points_from_set(s: list[Card]) -> int:
    """Legacy alias. See module docstring."""
    return points_for_set(s)
