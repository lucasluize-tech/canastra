"""Tests for the redacted PlayerView projection."""

from canastra.engine import GameConfig, PlayerView, initial_state


def test_view_for_reveals_own_hand():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=7)
    state = initial_state(cfg)
    view = state.view_for(seat=0)
    assert isinstance(view, PlayerView)
    assert view.own_seat == 0
    assert view.own_hand == state.hands[0]


def test_view_for_redacts_other_hands_to_counts():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=7)
    state = initial_state(cfg)
    view = state.view_for(seat=0)
    for seat in (1, 2, 3):
        assert view.hand_counts[seat] == len(state.hands[seat])


def test_view_for_redacts_deck_and_reserves_to_counts():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=7)
    state = initial_state(cfg)
    view = state.view_for(seat=2)
    assert view.deck_remaining == len(state.deck)
    # reserves_remaining is the count of unused reserve hands per team
    assert view.reserves_remaining[0] == cfg.reserves_per_team - state.reserves_used.get(0, 0)
    assert view.reserves_remaining[1] == cfg.reserves_per_team - state.reserves_used.get(1, 0)


def test_view_for_includes_public_table():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=7)
    state = initial_state(cfg)
    view = state.view_for(seat=0)
    assert view.trash == state.trash
    assert view.melds == state.melds
    assert view.current_turn == state.current_turn
    assert view.phase == state.phase


def test_view_for_round_trips_through_json():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=7)
    state = initial_state(cfg)
    view = state.view_for(seat=1)
    blob = view.model_dump_json()
    restored = PlayerView.model_validate_json(blob)
    assert restored.own_seat == 1
    assert restored.own_hand == view.own_hand
