"""Pure formatter tests for cli/render.py."""

from __future__ import annotations

import re
from uuid import UUID

from canastra.cli.render import (
    format_error,
    format_events,
    format_hand,
    format_score,
    format_table,
)
from canastra.domain.cards import Card
from canastra.engine import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    GameConfig,
    GameEnded,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    ScoreBreakdown,
    TrashPickedUp,
    TurnAdvanced,
    initial_state,
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
        assert "7♥" in out

    def test_numbers_are_one_based(self) -> None:
        hand = [Card("♥", 7), Card("♠", "King"), Card("♦", 2)]
        out = _strip_ansi(format_hand(hand))
        assert "1" in out and "2" in out and "3" in out

    def test_preserves_order(self) -> None:
        # Hearts sort before Spades, so 7♥ comes before K♠ in the sorted display.
        hand = [Card("♠", "King"), Card("♥", 7)]
        out = _strip_ansi(format_hand(hand))
        idx7 = out.index("7")
        idxK = out.index("K")
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


def test_format_table_happy() -> None:
    config = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    state = initial_state(config)
    out = _strip_ansi(format_table(state, viewing_player_id=0, names=_NAMES))
    assert "Ana" in out  # current player
    # Headers use "TEAM 0 — yellow" / "TEAM 1 — blue", parenthesized form
    # "(Team 0)" on the banner line.
    assert "TEAM 0" in out and "TEAM 1" in out
    assert "deck" in out.lower() or "cards" in out.lower()
    assert "trash" in out.lower()


def test_format_table_shows_trash_top() -> None:
    config = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    state = initial_state(config)
    state = state.model_copy(update={"trash": [Card("♠", "King")]})
    out = _strip_ansi(format_table(state, viewing_player_id=0, names=_NAMES))
    assert "K♠" in out


def test_format_table_lists_melds_by_team() -> None:
    from canastra.engine import Meld

    config = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    state = initial_state(config)
    meld = Meld(cards=[Card("♥", 7), Card("♥", 8), Card("♥", 9)])
    state = state.model_copy(update={"melds": {0: [meld], 1: []}})
    out = _strip_ansi(format_table(state, viewing_player_id=0, names=_NAMES))
    assert "7" in out and "8" in out and "9" in out


class TestFormatScore:
    def test_breakdown_printed_per_team(self) -> None:
        breakdowns = {
            0: ScoreBreakdown(
                leftover_debt=0,
                canastra_bonus=200,
                table_points=180,
                reserve_bonus=100,
                chin_bonus=100,
                total=580,
            ),
            1: ScoreBreakdown(
                leftover_debt=-50,
                canastra_bonus=0,
                table_points=90,
                reserve_bonus=0,
                chin_bonus=0,
                total=40,
            ),
        }
        out = _strip_ansi(format_score(breakdowns, _NAMES))
        assert "Team 0" in out and "Team 1" in out
        assert "580" in out and "40" in out
        assert "canastra" in out.lower()

    def test_declares_winner(self) -> None:
        breakdowns = {
            0: ScoreBreakdown(
                leftover_debt=0,
                canastra_bonus=200,
                table_points=180,
                reserve_bonus=100,
                chin_bonus=100,
                total=580,
            ),
            1: ScoreBreakdown(
                leftover_debt=0,
                canastra_bonus=0,
                table_points=40,
                reserve_bonus=0,
                chin_bonus=0,
                total=40,
            ),
        }
        out = _strip_ansi(format_score(breakdowns, _NAMES))
        assert "Team 0" in out
        assert "win" in out.lower()

    def test_declares_tie(self) -> None:
        breakdowns = {
            0: ScoreBreakdown(
                leftover_debt=0,
                canastra_bonus=0,
                table_points=100,
                reserve_bonus=0,
                chin_bonus=0,
                total=100,
            ),
            1: ScoreBreakdown(
                leftover_debt=0,
                canastra_bonus=0,
                table_points=100,
                reserve_bonus=0,
                chin_bonus=0,
                total=100,
            ),
        }
        out = _strip_ansi(format_score(breakdowns, _NAMES))
        assert "tie" in out.lower() or "tied" in out.lower()
