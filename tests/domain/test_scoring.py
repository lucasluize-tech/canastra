"""Scoring tests for ``canastra.domain.scoring``."""

from __future__ import annotations

import pytest

from canastra.domain.cards import HEARTS, Card
from canastra.domain.scoring import points_for_set, points_from_set


def _run(ranks: list[object]) -> list[Card]:
    return [Card(HEARTS, r) for r in ranks]


class TestPointsForSet:
    @pytest.mark.xfail(
        reason=(
            "Phase 2: scoring checks s[0] and s[1] without sorting — misses the "
            "A-low+A-high case when the list is not pre-sorted. Fix in Phase 2 by "
            "detecting 'contains two Aces and len==14' instead of positional checks."
        ),
        strict=True,
    )
    def test_ace_low_plus_ace_high_1000(self) -> None:
        ranks: list[object] = [
            "Ace",
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            "Jack",
            "Queen",
            "King",
            "Ace",
        ]
        assert points_for_set(_run(ranks)) == 1000

    def test_two_to_ace_500(self) -> None:
        ranks: list[object] = [
            "Ace",
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            "Jack",
            "Queen",
            "King",
        ]
        assert points_for_set(_run(ranks)) == 500

    def test_seven_card_natural_clean(self) -> None:
        assert points_for_set(_run([3, 4, 5, 6, 7, 8, 9])) == 200

    def test_seven_card_dirty_100(self) -> None:
        """Set with wild in middle: length 7, not clean → 100."""
        assert points_for_set(_run([3, 4, 5, 2, 7, 8, 9])) == 100

    def test_short_set_scores_zero(self) -> None:
        assert points_for_set(_run([3, 4, 5])) == 0


class TestPointsFromSetAlias:
    def test_alias_matches(self) -> None:
        assert points_from_set(_run([3, 4, 5])) == points_for_set(_run([3, 4, 5]))
