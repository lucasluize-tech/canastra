"""Tests for cli/setup.py — interactive GameConfig builder."""

from __future__ import annotations

import pytest

from canastra.cli.setup import build_config_interactive
from canastra.engine import GameConfig


def _scripted(inputs: list[str]):
    it = iter(inputs)
    return lambda _prompt: next(it)


def test_happy_path_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "42")
    inputs = [
        "",  # num_players (default 4)
        "",  # num_decks (default 2)
        "",  # reserves_per_team (default 2)
        "Ana",
        "Bruno",
        "Carla",
        "Davi",
    ]
    config, names = build_config_interactive(
        input_fn=_scripted(inputs),
        output_fn=lambda _: None,
    )
    assert isinstance(config, GameConfig)
    assert config.num_players == 4
    assert config.num_decks == 2
    assert config.reserves_per_team == 2
    assert config.seed == 42
    assert names == ["Ana", "Bruno", "Carla", "Davi"]


def test_reprompts_on_odd_players(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "7")
    inputs = [
        "5",  # rejected (odd)
        "3",  # rejected (below min)
        "6",  # accepted
        "",  # num_decks default
        "",  # reserves default
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
    ]
    outputs: list[str] = []
    config, _ = build_config_interactive(
        input_fn=_scripted(inputs),
        output_fn=outputs.append,
    )
    assert config.num_players == 6
    assert len([o for o in outputs if "number" in o.lower() or "even" in o.lower()]) >= 2


def test_reprompts_on_reserves_exceeding_decks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "7")
    inputs = [
        "4",
        "2",  # 2 decks
        "3",  # rejected (reserves > decks)
        "2",  # accepted
        "A",
        "B",
        "C",
        "D",
    ]
    outputs: list[str] = []
    config, _ = build_config_interactive(
        input_fn=_scripted(inputs),
        output_fn=outputs.append,
    )
    assert config.reserves_per_team == 2


def test_respects_canastra_seed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "123456")
    config, _ = build_config_interactive(
        input_fn=_scripted(["", "", "", "a", "b", "c", "d"]),
        output_fn=lambda _: None,
    )
    assert config.seed == 123456


def test_generates_random_seed_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CANASTRA_SEED", raising=False)
    config, _ = build_config_interactive(
        input_fn=_scripted(["", "", "", "a", "b", "c", "d"]),
        output_fn=lambda _: None,
    )
    assert isinstance(config.seed, int)
    assert 0 <= config.seed < 2**31


def test_empty_name_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "1")
    inputs = ["", "", "", "Ana", "", "Carla", "   "]  # players 2 and 4 blank
    config, names = build_config_interactive(
        input_fn=_scripted(inputs),
        output_fn=lambda _: None,
    )
    assert config.num_players == 4
    assert names == ["Ana", "Player2", "Carla", "Player4"]


def test_malformed_canastra_seed_warns_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANASTRA_SEED", "not-a-number")
    outputs: list[str] = []
    config, _ = build_config_interactive(
        input_fn=_scripted(["", "", "", "a", "b", "c", "d"]),
        output_fn=outputs.append,
    )
    assert isinstance(config.seed, int)
    assert 0 <= config.seed < 2**31
    assert any("CANASTRA_SEED" in o for o in outputs)
