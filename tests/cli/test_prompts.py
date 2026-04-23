"""Pure parser tests for cli/prompts.py."""

from __future__ import annotations

import pytest

from canastra.cli.prompts import (
    BadInput,
    parse_card_indices,
    parse_choice,
    parse_int_in_range,
    parse_yes_no,
)


class TestParseCardIndices:
    def test_single_index(self) -> None:
        assert parse_card_indices("3", hand_size=11) == [3]

    def test_comma_separated(self) -> None:
        assert parse_card_indices("1,2,3", hand_size=11) == [1, 2, 3]

    def test_with_spaces(self) -> None:
        assert parse_card_indices(" 1, 2 , 3 ", hand_size=11) == [1, 2, 3]

    def test_preserves_input_order(self) -> None:
        assert parse_card_indices("3,1,2", hand_size=11) == [3, 1, 2]

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_card_indices("", hand_size=11)

    def test_non_integer_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_card_indices("1,x,3", hand_size=11)

    def test_zero_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_card_indices("0", hand_size=11)

    def test_index_over_hand_size_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_card_indices("12", hand_size=11)

    def test_duplicate_indices_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_card_indices("1,1,2", hand_size=11)


class TestParseYesNo:
    @pytest.mark.parametrize("raw", ["y", "Y", "yes", "YES", " y "])
    def test_yes(self, raw: str) -> None:
        assert parse_yes_no(raw) is True

    @pytest.mark.parametrize("raw", ["n", "N", "no", "NO", " n "])
    def test_no(self, raw: str) -> None:
        assert parse_yes_no(raw) is False

    @pytest.mark.parametrize("raw", ["", "maybe", "1", "yep"])
    def test_invalid(self, raw: str) -> None:
        with pytest.raises(BadInput):
            parse_yes_no(raw)


class TestParseChoice:
    def test_valid_choice(self) -> None:
        assert parse_choice("d", {"d", "t"}) == "d"

    def test_case_insensitive(self) -> None:
        assert parse_choice("D", {"d", "t"}) == "d"

    def test_with_spaces(self) -> None:
        assert parse_choice(" t ", {"d", "t"}) == "t"

    def test_invalid_choice_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_choice("x", {"d", "t"})

    def test_empty_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_choice("", {"d", "t"})


class TestParseIntInRange:
    def test_in_range(self) -> None:
        assert parse_int_in_range("5", lo=1, hi=11) == 5

    def test_low_boundary(self) -> None:
        assert parse_int_in_range("1", lo=1, hi=11) == 1

    def test_high_boundary(self) -> None:
        assert parse_int_in_range("11", lo=1, hi=11) == 11

    def test_below_range_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_int_in_range("0", lo=1, hi=11)

    def test_above_range_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_int_in_range("12", lo=1, hi=11)

    def test_non_integer_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_int_in_range("x", lo=1, hi=11)

    def test_empty_rejected(self) -> None:
        with pytest.raises(BadInput):
            parse_int_in_range("", lo=1, hi=11)
