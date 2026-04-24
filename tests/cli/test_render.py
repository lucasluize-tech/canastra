"""Pure formatter tests for cli/render.py."""

from __future__ import annotations

import re
from uuid import UUID

from canastra.cli.render import format_error, format_events, format_hand
from canastra.domain.cards import Card
from canastra.engine import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    GameEnded,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    TrashPickedUp,
    TurnAdvanced,
)


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


_NAMES = ["Ana", "Bruno", "Carla", "Davi"]
_MELD_ID = UUID("12345678-1234-1234-1234-123456789abc")


class TestFormatEvents:
    def test_empty(self) -> None:
        assert format_events([], _NAMES) == []

    def test_card_drawn_private(self) -> None:
        lines = format_events([CardDrawn(player_id=0, card=Card("♥", 7))], _NAMES)
        assert len(lines) == 1
        out = _strip_ansi(lines[0])
        assert "Ana" in out
        assert "drew" in out.lower() or "draw" in out.lower()

    def test_trash_picked_up(self) -> None:
        ev = TrashPickedUp(player_id=1, cards=[Card("♣", 5), Card("♣", 6)])
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "Bruno" in out
        assert "trash" in out.lower()
        assert "2" in out  # count of cards

    def test_meld_created(self) -> None:
        ev = MeldCreated(
            player_id=2,
            team_id=0,
            meld_id=_MELD_ID,
            cards=[Card("♥", 7), Card("♥", 8), Card("♥", 9)],
        )
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "Team 0" in out or "team 0" in out.lower() or "Carla" in out
        assert "meld" in out.lower() or "created" in out.lower()

    def test_meld_extended(self) -> None:
        ev = MeldExtended(
            player_id=0,
            team_id=0,
            meld_id=_MELD_ID,
            added=[Card("♥", 10)],
        )
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "extend" in out.lower()

    def test_discarded(self) -> None:
        ev = Discarded(player_id=3, card=Card("♠", "King"))
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "Davi" in out
        assert "discard" in out.lower()

    def test_reserve_taken(self) -> None:
        ev = ReserveTaken(player_id=0, team_id=0, reserves_remaining=1)
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "reserve" in out.lower()
        assert "Ana" in out

    def test_deck_replenished(self) -> None:
        ev = DeckReplenished(team_id=1, cards_added=11)
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "deck" in out.lower()
        assert "replenish" in out.lower() or "reshuffle" in out.lower()

    def test_turn_advanced_is_silent(self) -> None:
        # TurnAdvanced should produce zero lines — the next turn's header
        # announces the new player.
        assert format_events([TurnAdvanced(next_player_id=1)], _NAMES) == []

    def test_chinned(self) -> None:
        ev = Chinned(team_id=0)
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "chin" in out.lower()
        assert "0" in out or "Team" in out

    def test_game_ended(self) -> None:
        ev = GameEnded(winning_team=0, scores={0: 1500, 1: 800})
        out = _strip_ansi(format_events([ev], _NAMES)[0])
        assert "game" in out.lower() and "over" in out.lower()

    def test_multiple_events_ordered(self) -> None:
        events = [
            Discarded(player_id=0, card=Card("♠", "King")),
            TurnAdvanced(next_player_id=1),
        ]
        lines = format_events(events, _NAMES)
        # Discarded produces a line, TurnAdvanced does not.
        assert len(lines) == 1
        assert "Ana" in _strip_ansi(lines[0])
