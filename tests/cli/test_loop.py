"""Per-phase helper + end-to-end tests for cli/loop.py."""

from __future__ import annotations

from canastra.cli.loop import _do_draw_phase
from canastra.domain.cards import Card
from canastra.engine import (
    CardDrawn,
    GameConfig,
    Phase,
    TrashPickedUp,
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
