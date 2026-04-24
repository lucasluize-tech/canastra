"""Interactive CLI turn loop over canastra.engine.

run() is the public entry point. Per-phase helpers (_do_draw_phase,
_do_play_phase, _do_discard) take the current state + names + injected
I/O and return (new_state, events). The loop orchestrates them.
"""

from __future__ import annotations

from collections.abc import Callable

from canastra.cli.prompts import ask_choice
from canastra.cli.render import format_error, format_events
from canastra.engine import (
    ActionRejected,
    Draw,
    Event,
    GameState,
    PickUpTrash,
    apply,
)


def run(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    raise NotImplementedError("filled in by Task 11")


def _do_draw_phase(
    state: GameState,
    *,
    names: list[str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> tuple[GameState, list[Event]]:
    """Ask 'd/t' and apply Draw or PickUpTrash. Reprompt on rejection."""
    pid = state.current_turn.player_id
    while True:
        choice = ask_choice(
            "Draw from deck or trash? (d/t): ",
            {"d", "t"},
            input_fn=input_fn,
            output_fn=output_fn,
        )
        action = Draw(player_id=pid) if choice == "d" else PickUpTrash(player_id=pid)
        try:
            new_state, events = apply(state, action)
        except ActionRejected as e:
            output_fn(format_error(str(e)))
            continue
        for line in format_events(events, names):
            output_fn(line)
        return new_state, events
