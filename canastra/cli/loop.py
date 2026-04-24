"""Interactive CLI turn loop over canastra.engine.

run() is the public entry point. Per-phase helpers (_do_draw_phase,
_do_play_phase, _do_discard) take the current state + names + injected
I/O and return (new_state, events). The loop orchestrates them.
"""

from __future__ import annotations

from collections.abc import Callable

from canastra.cli.prompts import BadInput, ask_choice, ask_int_in_range, parse_card_indices
from canastra.cli.render import format_error, format_events, format_hand
from canastra.engine import (
    ActionRejected,
    CreateMeld,
    Draw,
    Event,
    ExtendMeld,
    GameState,
    Meld,
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
    """Ask 'd/t' and apply Draw or PickUpTrash. Reprompt on rejection.

    Precondition: state.current_turn.phase == Phase.WAITING_DRAW.
    """
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


def _do_play_phase(
    state: GameState,
    *,
    names: list[str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> tuple[GameState, list[Event], str]:
    """Run one meld attempt OR signal discard-request.

    Loops internally until the player either plays a valid meld
    (returns kind="meld") or asks to move to discard (kind="discard_requested").
    The caller (run()) invokes this in an outer loop; each successful meld
    returns so the caller can decide whether to continue playing or stop.

    Precondition: state.current_turn.phase == Phase.PLAYING.
    """
    pid = state.current_turn.player_id
    while True:
        hand = state.hands[pid]
        output_fn(format_hand(hand))
        raw = input_fn("Play a set or 'd' to move to discard: ")
        if raw.strip().lower() == "d":
            return state, [], "discard_requested"

        try:
            indices = parse_card_indices(raw, hand_size=len(hand))
        except BadInput as e:
            output_fn(format_error(str(e)))
            continue

        cards = [hand[i - 1] for i in indices]

        target = ask_choice(
            "New set or extend existing? (n/e): ",
            {"n", "e"},
            input_fn=input_fn,
            output_fn=output_fn,
        )

        team_id = _team_for(state, pid)
        action: CreateMeld | ExtendMeld
        if target == "n":
            action = CreateMeld(player_id=pid, cards=cards)
        else:
            team_melds = state.melds.get(team_id, [])
            if not team_melds:
                output_fn(format_error("no existing melds to extend"))
                continue
            for i, m in enumerate(team_melds):
                output_fn(f"  [{i}] {_meld_line_for_listing(m)}")
            idx = ask_int_in_range(
                "Which meld (index)? ",
                lo=0,
                hi=len(team_melds) - 1,
                input_fn=input_fn,
                output_fn=output_fn,
            )
            meld_id = team_melds[idx].id
            action = ExtendMeld(player_id=pid, meld_id=meld_id, cards=cards)

        try:
            new_state, events = apply(state, action)
        except ActionRejected as e:
            output_fn(format_error(str(e)))
            continue

        for line in format_events(events, names):
            output_fn(line)
        return new_state, events, "meld"


def _team_for(state: GameState, player_id: int) -> int:
    for team_id, members in state.teams.items():
        if player_id in members:
            return team_id
    return -1


def _meld_line_for_listing(m: Meld) -> str:
    """Format a meld for the extend-meld selection list."""
    cards = " ".join(str(c) for c in m.cards)
    flag = " [dirty]" if m.permanent_dirty else ""
    short = str(m.id)[:6]
    return f"{cards}  (id: {short}){flag}"
