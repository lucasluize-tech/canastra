"""CLI output formatting.

Every function is pure: it takes values, returns a string. No I/O, no
state, no side effects. The loop decides when to print.

Color codes come from `colored`, matching the legacy main.py palette:
    team 0:   yellow
    team 1:   blue
    errors:   white-on-dark-red
    prompts:  dark-bg bold  (handled in prompts.py/loop.py, not here)
"""

from __future__ import annotations

from uuid import UUID

from colored import Back, Fore, Style

from canastra.domain.cards import Card
from canastra.engine import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    Event,
    GameEnded,
    GameState,
    Meld,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    ScoreBreakdown,
    TrashPickedUp,
    TurnAdvanced,
)

_ERROR_ON = f"{Fore.white}{Back.dark_red_1}"
_RESET = f"{Style.reset}"

_TEAM_COLORS = {0: Fore.yellow, 1: Fore.blue}


def _team_color(team_id: int) -> str:
    return _TEAM_COLORS.get(team_id, "")


def _cards_inline(cards: list[Card]) -> str:
    return " ".join(str(c) for c in cards)


def _meld_short(meld_id: UUID) -> str:
    return str(meld_id)[:6]


def format_error(message: str) -> str:
    """Red-on-dark-red error line for BadInput or ActionRejected."""
    return f"{_ERROR_ON}  {message}{_RESET}"


def format_hand(hand: list[Card]) -> str:
    """Numbered 1-based card list for the active player's hand."""
    if not hand:
        return "(hand is empty)"
    lines = [f"  {i + 1:>2}. {card}" for i, card in enumerate(hand)]
    return "\n".join(lines)


def format_events(events: list[Event], names: list[str]) -> list[str]:
    """Render a list of engine Events as human-readable lines.

    Silent events (currently just TurnAdvanced) return no line. The
    next turn's header announces the new player, so double-printing
    would be noise.
    """
    lines: list[str] = []
    for ev in events:
        line = _format_one(ev, names)
        if line is not None:
            lines.append(line)
    return lines


def _format_one(ev: Event, names: list[str]) -> str | None:
    if isinstance(ev, CardDrawn):
        name = names[ev.player_id]
        return f"  {name} drew {ev.card} from the deck"
    if isinstance(ev, TrashPickedUp):
        name = names[ev.player_id]
        return f"  {name} picked up the trash (+{len(ev.cards)} cards)"
    if isinstance(ev, MeldCreated):
        color = _team_color(ev.team_id)
        name = names[ev.player_id]
        meld = _cards_inline(ev.cards)
        return (
            f"  {color}{name} (Team {ev.team_id}) "
            f"created meld: {meld}  (id: {_meld_short(ev.meld_id)}){_RESET}"
        )
    if isinstance(ev, MeldExtended):
        color = _team_color(ev.team_id)
        name = names[ev.player_id]
        added = _cards_inline(ev.added)
        return (
            f"  {color}{name} (Team {ev.team_id}) "
            f"extended meld {_meld_short(ev.meld_id)} with: {added}{_RESET}"
        )
    if isinstance(ev, Discarded):
        name = names[ev.player_id]
        return f"  {name} discarded {ev.card}"
    if isinstance(ev, ReserveTaken):
        color = _team_color(ev.team_id)
        name = names[ev.player_id]
        return (
            f"  {color}{name}'s hand was empty — "
            f"Team {ev.team_id} took a reserve hand ({ev.reserves_remaining} remaining){_RESET}"
        )
    if isinstance(ev, DeckReplenished):
        color = _team_color(ev.team_id)
        return (
            f"  {color}Deck empty — replenished with {ev.cards_added} cards "
            f"from Team {ev.team_id}'s reserve{_RESET}"
        )
    if isinstance(ev, TurnAdvanced):
        return None  # silent
    if isinstance(ev, Chinned):
        color = _team_color(ev.team_id)
        return f"  {color}Team {ev.team_id} chinned!{_RESET}"
    if isinstance(ev, GameEnded):
        scored = ", ".join(f"Team {t}: {s}" for t, s in sorted(ev.scores.items()))
        return f"  Game over. {scored}"
    return f"  (unknown event: {ev!r})"  # pragma: no cover


def format_table(state: GameState, viewing_player_id: int, names: list[str]) -> str:
    """Render the visible table state as a multi-line string.

    Shows: current player + their team, each team's melds, trash top
    card, deck size, and per-team reserves-used count. Does NOT reveal
    other players' hands — only the viewing player's is rendered
    elsewhere via format_hand.
    """
    lines: list[str] = []
    current_pid = state.current_turn.player_id
    current_team = _team_for(state, current_pid)
    current_color = _team_color(current_team)

    lines.append("")
    lines.append(
        f"{current_color}========= {names[current_pid]} "
        f"(Team {current_team}) =========={_RESET}"
    )
    lines.append(f"  Deck: {len(state.deck)} cards   Trash top: {_trash_top(state)}")
    lines.append("")

    for team_id in (0, 1):
        color = _team_color(team_id)
        melds = state.melds.get(team_id, [])
        reserves_used = state.reserves_used.get(team_id, 0)
        reserves_total = state.config.reserves_per_team
        lines.append(
            f"  {color}Team {team_id} — melds: {len(melds)}, "
            f"reserves used: {reserves_used}/{reserves_total}{_RESET}"
        )
        for m in melds:
            lines.append(f"    {_meld_line(m)}")
    lines.append("")
    return "\n".join(lines)


def _team_for(state: GameState, player_id: int) -> int:
    for team_id, members in state.teams.items():
        if player_id in members:
            return team_id
    return -1


def _trash_top(state: GameState) -> str:
    return str(state.trash[-1]) if state.trash else "(empty)"


def _meld_line(m: Meld) -> str:
    cards = _cards_inline(m.cards)
    flag = " [dirty]" if m.permanent_dirty else ""
    return f"{cards}  (id: {_meld_short(m.id)}){flag}"


def format_score(
    breakdowns: dict[int, ScoreBreakdown],
    names: list[str],
) -> str:
    """Render per-team ScoreBreakdown and declare winner / tie."""
    lines: list[str] = ["", "============ FINAL SCORE ============"]
    for team_id in sorted(breakdowns):
        bd = breakdowns[team_id]
        color = _team_color(team_id)
        lines.append(f"{color}Team {team_id}{_RESET}")
        lines.append(f"  leftover debt:  {bd.leftover_debt}")
        lines.append(f"  canastra bonus: {bd.canastra_bonus}")
        lines.append(f"  table points:   {bd.table_points}")
        lines.append(f"  reserve bonus:  {bd.reserve_bonus}")
        lines.append(f"  chin bonus:     {bd.chin_bonus}")
        lines.append(f"  TOTAL:          {bd.total}")
        lines.append("")

    totals = {tid: bd.total for tid, bd in breakdowns.items()}
    max_total = max(totals.values())
    winners = [t for t, s in totals.items() if s == max_total]
    if len(winners) == 1:
        w = winners[0]
        lines.append(f"{_team_color(w)}Team {w} wins with {max_total} points!{_RESET}")
    else:
        tied = ", ".join(f"Team {t}" for t in winners)
        lines.append(f"Tied at {max_total}: {tied}")
    return "\n".join(lines)
