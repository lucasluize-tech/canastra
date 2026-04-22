"""Determinism: (seed, action_log) -> final state is stable."""

from __future__ import annotations

from canastra.engine import (
    Discard,
    Draw,
    GameConfig,
    apply,
    initial_state,
)


def _naive_turn(state):
    """Replay helper: draw then discard the first hand card."""
    pid = state.current_turn.player_id
    s, _ = apply(state, Draw(player_id=pid))
    s, _ = apply(s, Discard(player_id=pid, card=s.hands[pid][0]))
    return s


def test_replay_identical_for_same_seed():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=777)
    s1 = initial_state(cfg)
    s2 = initial_state(cfg)
    for _ in range(12):  # 3 rotations of 4 players
        s1 = _naive_turn(s1)
        s2 = _naive_turn(s2)
    assert s1.model_dump_json() == s2.model_dump_json()


def test_replay_different_for_different_seed():
    cfg_a = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=1)
    cfg_b = cfg_a.model_copy(update={"seed": 2})
    s_a = initial_state(cfg_a)
    s_b = initial_state(cfg_b)
    for _ in range(4):
        s_a = _naive_turn(s_a)
        s_b = _naive_turn(s_b)
    assert s_a != s_b


def test_serialize_mid_game_and_resume():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=55)
    s = initial_state(cfg)
    for _ in range(4):
        s = _naive_turn(s)
    blob = s.model_dump_json()

    # Simulate full restart
    from canastra.engine import GameState

    s_restored = GameState.model_validate_json(blob)
    # Play one more turn from both; results must match.
    s_direct = _naive_turn(s)
    s_restored = _naive_turn(s_restored)
    assert s_direct.model_dump_json() == s_restored.model_dump_json()
