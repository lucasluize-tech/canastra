from __future__ import annotations

import pytest

from canastra.engine.state import GameConfig


@pytest.fixture
def cfg_4p2d() -> GameConfig:
    return GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=12345)


@pytest.fixture
def cfg_6p6d() -> GameConfig:
    return GameConfig(num_players=6, num_decks=6, reserves_per_team=3, timer_enabled=False, seed=999)
