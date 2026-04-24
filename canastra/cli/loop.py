"""Interactive CLI turn loop over canastra.engine.

run() is the public entry point. Per-phase helpers (_do_draw_phase,
_do_play_phase, _do_discard) take the current state + names + injected
I/O and return (new_state, events). The loop orchestrates them.
"""

from __future__ import annotations

from collections.abc import Callable

from canastra.cli.prompts import (
    BadInput,
    ask_choice,
    ask_int_in_range,
    ask_yes_no,
    parse_card_indices,
)
from canastra.cli.render import (
    format_error,
    format_events,
    format_hand,
    format_score,
    format_table,
)
from canastra.cli.setup import build_config_interactive
from canastra.domain.rules import extends_set, run_order
from canastra.engine import (
    ActionRejected,
    CreateMeld,
    Discard,
    Draw,
    Event,
    ExtendMeld,
    GameState,
    Meld,
    Phase,
    PickUpTrash,
    apply,
    end_of_game_score,
    initial_state,
)


def run(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Play an interactive Canastra game to completion.

    Returns:
        0 on normal end-of-game.
        130 on EOFError / KeyboardInterrupt (Unix convention).
    """
    try:
        config, names = build_config_interactive(input_fn=input_fn, output_fn=output_fn)
    except (EOFError, KeyboardInterrupt):
        output_fn("\nGame canceled during setup.")
        return 130

    state = initial_state(config)

    try:
        while state.phase != Phase.ENDED:
            pid = state.current_turn.player_id
            output_fn(format_table(state, viewing_player_id=pid, names=names))
            output_fn(format_hand(state.hands[pid]))

            if state.current_turn.phase == Phase.WAITING_DRAW:
                state, _ = _do_draw_phase(
                    state, names=names, input_fn=input_fn, output_fn=output_fn
                )
                continue

            # PLAYING (and/or transient DISCARDING): inner loop until discard or game end.
            while (
                state.current_turn.phase in {Phase.PLAYING, Phase.DISCARDING}
                and state.phase != Phase.ENDED
            ):
                new_state, _events, kind = _do_play_phase(
                    state, names=names, input_fn=input_fn, output_fn=output_fn
                )
                if kind == "discard_requested":
                    discard_result = _do_discard(
                        state, names=names, input_fn=input_fn, output_fn=output_fn
                    )
                    if discard_result is None:
                        # player canceled — stay in play loop
                        continue
                    state, _ = discard_result
                    break  # turn ends after successful discard
                # kind == "meld": state updated, keep playing
                state = new_state

    except (EOFError, KeyboardInterrupt):
        output_fn("\nGame canceled.")
        return 130

    # End-of-game scoring
    breakdowns = end_of_game_score(state)
    output_fn(format_score(breakdowns, names))
    return 0


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
        for line in format_events(events, names, state=new_state):
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
        # format_hand sorts internally; use the same sorted view for index lookup
        # so the card at position i in the displayed list matches hand[i - 1].
        hand = sorted(state.hands[pid])
        output_fn(format_hand(state.hands[pid]))
        raw = input_fn("Play a set or 'd' to move to discard: ")
        if raw.strip().lower() == "d":
            return state, [], "discard_requested"

        try:
            indices = parse_card_indices(raw, hand_size=len(hand))
        except BadInput as e:
            output_fn(format_error(str(e)))
            continue

        cards = [hand[i - 1] for i in indices]
        team_id = _team_for(state, pid)
        team_melds = state.melds.get(team_id, [])

        # Fewer than 3 cards can only be an extension (no new meld is that small).
        # Skip the n/e prompt in that case.
        if len(cards) < 3:
            target = "e"
        else:
            target = ask_choice(
                "New set or extend existing? (n/e): ",
                {"n", "e"},
                input_fn=input_fn,
                output_fn=output_fn,
            )

        action: CreateMeld | ExtendMeld
        if target == "n":
            action = CreateMeld(player_id=pid, cards=cards)
        else:
            extendable = [m for m in team_melds if extends_set(list(m.cards), cards)]
            if not extendable:
                output_fn(format_error("no existing meld can accept these cards"))
                continue
            if len(extendable) == 1:
                meld = extendable[0]
                output_fn(f"  auto-selected: {_meld_line_for_listing(meld)}")
                meld_id = meld.id
            else:
                for i, m in enumerate(extendable):
                    output_fn(f"  [{i}] {_meld_line_for_listing(m)}")
                idx = ask_int_in_range(
                    "Which meld (index)? ",
                    lo=0,
                    hi=len(extendable) - 1,
                    input_fn=input_fn,
                    output_fn=output_fn,
                )
                meld_id = extendable[idx].id
            action = ExtendMeld(player_id=pid, meld_id=meld_id, cards=cards)

        try:
            new_state, events = apply(state, action)
        except ActionRejected as e:
            output_fn(format_error(str(e)))
            continue

        for line in format_events(events, names, state=new_state):
            output_fn(line)
        return new_state, events, "meld"


def _team_for(state: GameState, player_id: int) -> int:
    for team_id, members in state.teams.items():
        if player_id in members:
            return team_id
    return -1


def _meld_line_for_listing(m: Meld) -> str:
    """Format a meld for the extend-meld selection list."""
    cards = " ".join(str(c) for c in run_order(list(m.cards)))
    flag = " [dirty]" if m.permanent_dirty else ""
    short = str(m.id)[:6]
    return f"{cards}  (id: {short}){flag}"


def _do_discard(
    state: GameState,
    *,
    names: list[str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> tuple[GameState, list[Event]] | None:
    """Discard sub-flow.

    Returns (new_state, events) on successful discard, or None if the
    player cancels at the confirmation step. Caller should drop back
    into the play loop on None.

    Precondition: state.current_turn.phase == Phase.PLAYING. The engine
    transitions to WAITING_DRAW for the next player on success.
    """
    pid = state.current_turn.player_id
    # format_hand sorts internally; keep our index lookup on the same sorted view.
    hand = sorted(state.hands[pid])
    output_fn(format_hand(state.hands[pid]))

    while True:
        idx = ask_int_in_range(
            "Which card to discard? ",
            lo=1,
            hi=len(hand),
            input_fn=input_fn,
            output_fn=output_fn,
        )
        card = hand[idx - 1]
        if not ask_yes_no(
            f"Discard {card}? (y/n): ",
            input_fn=input_fn,
            output_fn=output_fn,
        ):
            return None
        try:
            new_state, events = apply(state, Discard(player_id=pid, card=card))
        except ActionRejected as e:
            output_fn(format_error(str(e)))
            continue
        for line in format_events(events, names, state=new_state):
            output_fn(line)
        return new_state, events
