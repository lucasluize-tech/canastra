"""Pure formatter tests for cli/render.py."""

from __future__ import annotations

import re

from canastra.cli.render import format_error, format_hand
from canastra.domain.cards import Card


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape codes for snapshot comparisons."""
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


class TestFormatHand:
    def test_empty_hand(self) -> None:
        assert "empty" in _strip_ansi(format_hand([])).lower()

    def test_single_card(self) -> None:
        out = _strip_ansi(format_hand([Card("♥", 7)]))
        assert "1" in out
        assert "7" in out or "♥" in out

    def test_numbers_are_one_based(self) -> None:
        hand = [Card("♥", 7), Card("♠", "King"), Card("♦", 2)]
        out = _strip_ansi(format_hand(hand))
        assert "1" in out and "2" in out and "3" in out

    def test_preserves_order(self) -> None:
        hand = [Card("♥", 7), Card("♠", "King")]
        out = _strip_ansi(format_hand(hand))
        idx7 = out.index("7")
        idxK = out.index("King")
        assert idx7 < idxK


class TestFormatError:
    def test_contains_message(self) -> None:
        out = _strip_ansi(format_error("invalid meld"))
        assert "invalid meld" in out

    def test_has_error_decoration(self) -> None:
        raw = format_error("oops")
        assert "\x1b[" in raw or "[" in raw  # some decoration
