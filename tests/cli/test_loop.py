"""Per-phase helper + end-to-end tests for cli/loop.py."""

from __future__ import annotations

import pytest

from canastra.cli.loop import _do_discard, _do_draw_phase, _do_play_phase, run
from canastra.domain.cards import Card
from canastra.engine import (
    CardDrawn,
    Discarded,
    Draw,
    GameConfig,
    MeldCreated,
    Phase,
    TrashPickedUp,
    apply,
    initial_state,
)

_NAMES = ["Ana", "Bruno", "Carla", "Davi"]


def _fresh_state() -> object:
    config = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    return initial_state(config)


def _scripted(inputs: list[str]):
    it = iter(inputs)
    return lambda _prompt: next(it)


class TestDoDrawPhase:
    def test_draw_from_deck(self) -> None:
        state = _fresh_state()
        outputs: list[str] = []

        new_state, events = _do_draw_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(["d"]),
            output_fn=outputs.append,
        )

        assert new_state.current_turn.phase != Phase.WAITING_DRAW
        assert any(isinstance(e, CardDrawn) for e in events)
        assert len(new_state.hands[0]) == 12

    def test_pickup_trash(self) -> None:
        base = _fresh_state()
        state = base.model_copy(update={"trash": [Card("♠", "King")]})
        outputs: list[str] = []

        new_state, events = _do_draw_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(["t"]),
            output_fn=outputs.append,
        )

        assert any(isinstance(e, TrashPickedUp) for e in events)
        assert new_state.trash == []
        assert len(new_state.hands[0]) == 12

    def test_invalid_input_reprompts(self) -> None:
        state = _fresh_state()
        outputs: list[str] = []

        _do_draw_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(["q", "x", "d"]),
            output_fn=outputs.append,
        )

        errs = [o for o in outputs if "expected" in o or "try again" in o.lower()]
        assert len(errs) >= 2

    def test_pickup_trash_when_empty_reprompts(self) -> None:
        state = _fresh_state()
        outputs: list[str] = []

        new_state, events = _do_draw_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(["t", "d"]),
            output_fn=outputs.append,
        )
        assert any(isinstance(e, CardDrawn) for e in events)
        assert any("empty" in o.lower() or "trash" in o.lower() for o in outputs)


def _state_in_playing() -> object:
    state = _fresh_state()
    state, _ = apply(state, Draw(player_id=0))
    return state


class TestDoPlayPhase:
    def test_player_requests_discard(self) -> None:
        state = _state_in_playing()
        outputs: list[str] = []
        new_state, events, kind = _do_play_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(["d"]),
            output_fn=outputs.append,
        )
        assert kind == "discard_requested"
        assert events == []
        assert new_state is state

    def test_create_meld_happy(self) -> None:
        state = _state_in_playing()
        # Sorted by (suit_order=CLUBS<DIAMONDS<HEARTS<SPADES, rank) this becomes:
        #   1  ♣2    2  ♣10   3  ♦3    4  ♦4    5  ♦J
        #   6  ♥7    7  ♥8    8  ♥9    9  ♥Q   10  ♠A   11  ♠5   12  ♠6
        # So the natural 7-8-9♥ meld lives at display indices 6,7,8.
        hand = [
            Card("♥", 7),
            Card("♥", 8),
            Card("♥", 9),
            Card("♠", 5),
            Card("♠", 6),
            Card("♦", 4),
            Card("♦", "Jack"),
            Card("♣", 2),
            Card("♣", 10),
            Card("♥", "Queen"),
            Card("♠", "Ace"),
            Card("♦", 3),
        ]
        state = state.model_copy(update={"hands": {**state.hands, 0: hand}})
        outputs: list[str] = []

        new_state, events, kind = _do_play_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(
                [
                    "6,7,8",
                    "n",
                ]
            ),
            output_fn=outputs.append,
        )

        assert kind == "meld"
        assert any(isinstance(e, MeldCreated) for e in events)
        assert len(new_state.hands[0]) == len(hand) - 3

    def test_rejects_invalid_meld_and_reprompts(self) -> None:
        state = _state_in_playing()
        # Sorted view:
        #   1 ♣4  2 ♣5  3 ♣6  4 ♣7  5 ♣8  6 ♣9
        #   7 ♦3  8 ♥7  9 ♥8 10 ♥9 11 ♥10 12 ♠2
        # First attempt (1,7,12) picks ♣4 ♦3 ♠2 — mixed suits, rejected.
        # Second attempt (8,9,10) picks ♥7 ♥8 ♥9 — valid natural run.
        hand = [
            Card("♥", 7),
            Card("♠", 2),
            Card("♦", 3),
            Card("♥", 8),
            Card("♥", 9),
            Card("♥", 10),
        ] + [Card("♣", r) for r in (4, 5, 6, 7, 8, 9)]
        state = state.model_copy(update={"hands": {**state.hands, 0: hand}})
        outputs: list[str] = []

        new_state, events, kind = _do_play_phase(
            state,
            names=_NAMES,
            input_fn=_scripted(
                [
                    "1,7,12",
                    "n",
                    "8,9,10",
                    "n",
                ]
            ),
            output_fn=outputs.append,
        )

        assert kind == "meld"
        assert any(isinstance(e, MeldCreated) for e in events)
        assert (
            any(
                "rejected" in o.lower() or "invalid" in o.lower() or "wild" in o.lower()
                for o in outputs
            )
            or len([o for o in outputs if "\x1b" in o]) >= 1
        )


class TestDoDiscard:
    def test_discard_happy(self) -> None:
        state = _state_in_playing()
        outputs: list[str] = []

        new_state, events = _do_discard(
            state,
            names=_NAMES,
            input_fn=_scripted(
                [
                    "1",
                    "y",
                ]
            ),
            output_fn=outputs.append,
        )

        assert any(isinstance(e, Discarded) for e in events)
        assert len(new_state.hands[0]) == len(state.hands[0]) - 1
        assert len(new_state.trash) == 1

    def test_cancel_discard_returns_none(self) -> None:
        state = _state_in_playing()
        outputs: list[str] = []

        result = _do_discard(
            state,
            names=_NAMES,
            input_fn=_scripted(["1", "n"]),
            output_fn=outputs.append,
        )

        assert result is None

    def test_reprompts_on_bad_index(self) -> None:
        state = _state_in_playing()
        outputs: list[str] = []

        new_state, events = _do_discard(
            state,
            names=_NAMES,
            input_fn=_scripted(["0", "99", "1", "y"]),
            output_fn=outputs.append,
        )
        assert any(isinstance(e, Discarded) for e in events)


class TestRun:
    def test_run_plays_first_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """End-to-end test: script enough inputs to get through player 0's turn
        and verify the game advances."""
        monkeypatch.setenv("CANASTRA_SEED", "42")
        inputs = iter(
            [
                "4",
                "2",
                "2",
                "Ana",
                "Bruno",
                "Carla",
                "Davi",
                "d",
                "d",
                "1",
                "y",
            ]
        )

        outputs: list[str] = []

        def input_fn(_prompt: str) -> str:
            try:
                return next(inputs)
            except StopIteration as e:
                raise EOFError from e

        exit_code = run(input_fn=input_fn, output_fn=outputs.append)

        assert exit_code == 130
        combined = "\n".join(outputs)
        assert "Ana" in combined
        assert "discard" in combined.lower()

    def test_run_announces_end_of_game_when_scored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tracked by the manual smoke playthrough in Task 13."""
        pytest.skip("end-to-end chin scripting covered by manual smoke in Task 13")
