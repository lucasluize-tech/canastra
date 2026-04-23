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


from canastra.cli.prompts import (
    ask_card_indices,
    ask_choice,
    ask_int_in_range,
    ask_yes_no,
)


def _scripted(inputs: list[str]):
    """Return a callable that pops from a scripted input list."""
    it = iter(inputs)
    return lambda _prompt: next(it)


class TestAskWrappers:
    def test_ask_choice_happy(self) -> None:
        outputs: list[str] = []
        result = ask_choice(
            "Draw from deck or trash? (d/t)",
            {"d", "t"},
            input_fn=_scripted(["d"]),
            output_fn=outputs.append,
        )
        assert result == "d"
        assert outputs == []  # no error lines on happy path

    def test_ask_choice_reprompts_on_bad_input(self) -> None:
        outputs: list[str] = []
        result = ask_choice(
            "Draw from deck or trash? (d/t)",
            {"d", "t"},
            input_fn=_scripted(["x", "q", "t"]),
            output_fn=outputs.append,
        )
        assert result == "t"
        assert len(outputs) == 2  # two rejection messages before success

    def test_ask_yes_no_happy(self) -> None:
        result = ask_yes_no(
            "Continue?",
            input_fn=_scripted(["y"]),
            output_fn=lambda _: None,
        )
        assert result is True

    def test_ask_yes_no_reprompts(self) -> None:
        outputs: list[str] = []
        result = ask_yes_no(
            "Continue?",
            input_fn=_scripted(["maybe", "n"]),
            output_fn=outputs.append,
        )
        assert result is False
        assert len(outputs) == 1

    def test_ask_int_in_range_happy(self) -> None:
        result = ask_int_in_range(
            "How many?",
            lo=1,
            hi=11,
            input_fn=_scripted(["5"]),
            output_fn=lambda _: None,
        )
        assert result == 5

    def test_ask_int_in_range_reprompts(self) -> None:
        outputs: list[str] = []
        result = ask_int_in_range(
            "How many?",
            lo=1,
            hi=11,
            input_fn=_scripted(["0", "12", "x", "7"]),
            output_fn=outputs.append,
        )
        assert result == 7
        assert len(outputs) == 3

    def test_ask_card_indices_happy(self) -> None:
        result = ask_card_indices(
            "Which cards?",
            hand_size=11,
            input_fn=_scripted(["1,2,3"]),
            output_fn=lambda _: None,
        )
        assert result == [1, 2, 3]

    def test_ask_card_indices_reprompts(self) -> None:
        outputs: list[str] = []
        result = ask_card_indices(
            "Which cards?",
            hand_size=11,
            input_fn=_scripted(["0,1", "1,1", "1,2"]),
            output_fn=outputs.append,
        )
        assert result == [1, 2]
        assert len(outputs) == 2
