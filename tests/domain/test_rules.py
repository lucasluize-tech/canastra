"""Rule-function tests for ``canastra.domain.rules``.

Encodes the canonical family rules from the project memory note
``project_canastra_rules.md``. Tests marked ``xfail`` describe behavior the
Phase-1 verbatim port does NOT implement — they are the spec for Phase 2
to satisfy.
"""

from __future__ import annotations

from canastra.domain.cards import CLUBS, HEARTS, SPADES, Card
from canastra.domain.rules import extends_set, is_clean, is_in_order, is_permanent_dirty, rank_to_number


def _run(suit: str, ranks: list[object]) -> list[Card]:
    return [Card(suit, r) for r in ranks]


class TestRankToNumber:
    def test_ace_low_by_default(self) -> None:
        assert rank_to_number("Ace") == 1

    def test_ace_high_when_requested(self) -> None:
        assert rank_to_number("Ace", high_ace=True) == 14

    def test_face_cards(self) -> None:
        assert rank_to_number("Jack") == 11
        assert rank_to_number("Queen") == 12
        assert rank_to_number("King") == 13

    def test_numeric_ranks_passthrough(self) -> None:
        for r in range(2, 11):
            assert rank_to_number(r) == r


class TestIsInOrder:
    def test_simple_run(self) -> None:
        assert is_in_order(_run(HEARTS, [3, 4, 5]))

    def test_run_with_wild_in_middle(self) -> None:
        assert is_in_order(_run(HEARTS, [3, 2, 5]))

    def test_ace_low_run(self) -> None:
        assert is_in_order(_run(HEARTS, ["Ace", 2, 3]))

    def test_ace_high_run(self) -> None:
        assert is_in_order(_run(HEARTS, ["Jack", "Queen", "King", "Ace"]))

    def test_ace_low_plus_ace_high_14_card(self) -> None:
        """The 1000-point canastra: A, 2..K, A."""
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
        assert is_in_order(_run(HEARTS, ranks))


class TestIsClean:
    def test_clean_7_card_natural_run(self) -> None:
        assert is_clean(_run(HEARTS, [3, 4, 5, 6, 7, 8, 9]))

    def test_clean_with_natural_2_in_twos_slot(self) -> None:
        """Natural 2 of matching suit in rank-2 position: still clean."""
        assert is_clean(_run(HEARTS, [2, 3, 4, 5, 6, 7, 8]))

    def test_clean_with_ace_low_and_natural_2(self) -> None:
        assert is_clean(_run(HEARTS, ["Ace", 2, 3, 4, 5, 6, 7]))

    def test_too_short(self) -> None:
        assert not is_clean(_run(HEARTS, [3, 4, 5, 6, 7, 8]))

    def test_dirty_with_wild_in_middle(self) -> None:
        """Wild-2 filling a non-rank-2 slot → dirty, not clean."""
        assert not is_clean(_run(HEARTS, [3, 4, 5, 2, 7, 8, 9]))

    def test_permanent_dirty_wrong_suit_two(self) -> None:
        """2♣ used in a hearts set is a wild, not a natural 2 → not clean."""
        cards = [
            Card(CLUBS, 2),  # wild, occupies rank-2 slot
            Card(HEARTS, 3),
            Card(HEARTS, 4),
            Card(HEARTS, 5),
            Card(HEARTS, 6),
            Card(HEARTS, 7),
            Card(HEARTS, 8),
        ]
        assert not is_clean(cards)


class TestExtendsSet:
    def test_does_not_crash_on_first_iteration(self) -> None:
        """Phase-1 fix: legacy code raised NameError on ``prev`` here."""
        chosen = _run(HEARTS, ["Ace", 2, 3])
        addition = _run(HEARTS, [4])
        # Whether the rule returns True or False, it must not crash.
        assert extends_set(chosen, addition) in (True, False)

    def test_rejects_duplicate_non_wild_rank(self) -> None:
        assert not extends_set(_run(HEARTS, [3, 4, 5]), _run(HEARTS, [5]))

    def test_wild_reinterpret_on_extend(self) -> None:
        """Canonical rule: wilds reinterpret on extend.

        Set ``[8♥, 2♥, 10♥]`` (valid with 2=9) extended by ``[9♥, Q♥]``
        should produce ``[8,9,10,J=2,Q]`` — valid.

        The Phase-1 port returns True here *by accident* because it performs
        no run-structure check at all (see ``test_extends_accepts_invalid_run``
        below — that's the real gap). Phase 2 will introduce real validation
        that still returns True for this case via wild reinterpretation, so
        this test remains green across the transition.
        """
        chosen = _run(HEARTS, [8, 2, 10])
        addition = _run(HEARTS, [9, "Queen"])
        assert extends_set(chosen, addition)

    def test_extends_rejects_non_run_extension(self) -> None:
        """Legacy ``extends_set`` ignores run structure — accepts any non-duplicate.

        Extending ``[3,4,5]♥`` with ``[10♥]`` produces ``[3,4,5,10]`` which
        is not a run; rule says reject.
        """
        assert not extends_set(_run(HEARTS, [3, 4, 5]), _run(HEARTS, [10]))

    def test_rejects_third_wild_from_any_suit(self) -> None:
        chosen = [
            Card(HEARTS, 3),
            Card(HEARTS, 2),  # natural/wild
            Card(CLUBS, 2),  # wild (wrong suit)
            Card(HEARTS, 6),
        ]
        addition = [Card(SPADES, 2)]  # third wild
        assert not extends_set(chosen, addition)


class TestIsPermanentDirty:
    def test_permanent_dirty_wrong_suit_two_in_rank_2_slot(self) -> None:
        # 2 of SPADES occupies the heart run's rank-2 slot as a wild
        cards = [Card(HEARTS, "Ace"), Card(SPADES, 2), Card(HEARTS, 3), Card(HEARTS, 4)]
        assert is_permanent_dirty(cards) is True

    def test_permanent_dirty_natural_plus_wild_both_present(self) -> None:
        # 2 of HEARTS is the natural; 2 of SPADES is a wild elsewhere.
        cards = [
            Card(HEARTS, "Ace"),
            Card(HEARTS, 2),
            Card(HEARTS, 3),
            Card(HEARTS, 4),
            Card(SPADES, 2),
            Card(HEARTS, 6),
        ]
        assert is_permanent_dirty(cards) is True

    def test_dirty_but_not_permanent_wild_in_interior(self) -> None:
        # Wild at slot 9 can later be displaced by a natural 9
        cards = [Card(HEARTS, 7), Card(HEARTS, 8), Card(SPADES, 2), Card(HEARTS, 10)]
        assert is_permanent_dirty(cards) is False

    def test_clean_set_is_not_permanent_dirty(self) -> None:
        cards = [Card(HEARTS, r) for r in (3, 4, 5, 6, 7, 8, 9)]
        assert is_permanent_dirty(cards) is False

    def test_invalid_set_is_not_permanent_dirty(self) -> None:
        cards = [Card(HEARTS, 3), Card(SPADES, 4)]
        assert is_permanent_dirty(cards) is False
