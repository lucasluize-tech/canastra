"""End-of-game scoring.

Per-team breakdown, computed greedily against the card-removal rule in
project_canastra_rules.md. Exposed as pure functions so replay tests
can compare breakdowns directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from canastra.domain.rules import is_in_order
from canastra.domain.scoring import points_for_set
from canastra.engine.state import GameState, Meld, TeamId

_MIN_CANASTRA: int = 7
_CARD_POINTS: int = 10
_RESERVE_BONUS: int = 100
_CHIN_BONUS: int = 100


@dataclass(frozen=True)
class ScoreBreakdown:
    leftover_debt: int
    canastra_bonus: int
    table_points: int
    reserve_bonus: int
    chin_bonus: int
    total: int


def _is_canastra(m: Meld) -> bool:
    return len(m.cards) >= _MIN_CANASTRA and is_in_order(m.cards)


def _absorb_debt(melds: list[Meld], debt: int) -> list[Meld]:
    """Return a new melds list with `debt` points worth of cards removed.

    Algorithm:
      1. Remove whole non-canastra sets from cheapest (fewest cards) first.
      2. Trim canastras down to length 7 from longest-above-7 first.
      3. Sacrifice whole canastras from lowest bonus to highest.
      4. Any remaining debt is absorbed by the floor rule (caller floors
         the final total at 0).
    """
    remaining_debt = debt
    current = list(melds)

    # Step 1: whole non-canastra sets first (cheapest first)
    non_canastras = sorted(
        [m for m in current if not _is_canastra(m)], key=lambda m: len(m.cards)
    )
    for m in non_canastras:
        if remaining_debt <= 0:
            break
        cost = len(m.cards) * _CARD_POINTS
        if cost <= remaining_debt:
            current.remove(m)
            remaining_debt -= cost
        else:
            # Partially remove from this set
            cards_to_remove = remaining_debt // _CARD_POINTS
            new_cards = m.cards[cards_to_remove:]
            idx = current.index(m)
            current[idx] = Meld(id=m.id, cards=new_cards, permanent_dirty=m.permanent_dirty)
            remaining_debt -= cards_to_remove * _CARD_POINTS

    if remaining_debt <= 0:
        return current

    # Step 2: trim canastras down to length 7
    canastras = [m for m in current if _is_canastra(m)]
    canastras_sorted = sorted(canastras, key=lambda m: -len(m.cards))
    for m in canastras_sorted:
        if remaining_debt <= 0:
            break
        trimmable = len(m.cards) - _MIN_CANASTRA
        if trimmable <= 0:
            continue
        cards_to_remove = min(trimmable, remaining_debt // _CARD_POINTS)
        if cards_to_remove <= 0:
            continue
        new_cards = m.cards[cards_to_remove:]
        idx = current.index(m)
        current[idx] = Meld(id=m.id, cards=new_cards, permanent_dirty=m.permanent_dirty)
        remaining_debt -= cards_to_remove * _CARD_POINTS

    if remaining_debt <= 0:
        return current

    # Step 3: sacrifice canastras, lowest bonus first.
    # Only sacrifice a canastra when the remaining debt is >= its table value
    # (otherwise keeping the canastra is worth more than absorbing the debt).
    canastras = [m for m in current if _is_canastra(m)]
    canastras_by_bonus = sorted(canastras, key=lambda m: points_for_set(m.cards))
    for m in canastras_by_bonus:
        if remaining_debt <= 0:
            break
        cost = len(m.cards) * _CARD_POINTS
        if remaining_debt >= cost:
            current.remove(m)
            remaining_debt -= cost

    return current


def _team_canastra_bonus(melds: list[Meld]) -> int:
    return sum(points_for_set(m.cards) for m in melds if _is_canastra(m))


def _team_table_points(melds: list[Meld]) -> int:
    return sum(len(m.cards) for m in melds) * _CARD_POINTS


def _team_leftover(state: GameState, team_id: TeamId) -> int:
    return (
        sum(len(state.hands[pid]) for pid in state.teams[team_id]) * _CARD_POINTS
    )


def _team_breakdown(state: GameState, team_id: TeamId) -> ScoreBreakdown:
    leftover = _team_leftover(state, team_id)
    melds_after = _absorb_debt(state.melds[team_id], leftover)
    canastra_bonus = _team_canastra_bonus(melds_after)
    table_points = _team_table_points(melds_after)
    reserve_bonus = state.reserves_used[team_id] * _RESERVE_BONUS
    chin_bonus = _CHIN_BONUS if state.chin_team == team_id else 0
    total = max(canastra_bonus + table_points + reserve_bonus + chin_bonus, 0)
    return ScoreBreakdown(
        leftover_debt=leftover,
        canastra_bonus=canastra_bonus,
        table_points=table_points,
        reserve_bonus=reserve_bonus,
        chin_bonus=chin_bonus,
        total=total,
    )


def end_of_game_score(state: GameState) -> dict[TeamId, ScoreBreakdown]:
    return {team_id: _team_breakdown(state, team_id) for team_id in state.teams}
