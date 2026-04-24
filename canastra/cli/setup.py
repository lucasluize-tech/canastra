"""Interactive game-configuration prompts.

Returns a frozen GameConfig + the parallel player_names list. Seed
comes from CANASTRA_SEED if set (useful for reproducible manual
testing and scripted integration tests); otherwise a fresh random
value from os.urandom-backed SystemRandom.
"""

from __future__ import annotations

import os
import random
from collections.abc import Callable

from canastra.cli.prompts import BadInput, parse_int_in_range
from canastra.engine import GameConfig

_DEFAULT_PLAYERS = 4
_DEFAULT_DECKS = 2
_DEFAULT_RESERVES = 2

_MAX_PLAYERS = 32
_MAX_DECKS = 16


def build_config_interactive(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> tuple[GameConfig, list[str]]:
    """Prompt for player count / decks / reserves / names; return config."""
    num_players = _ask_int_with_default(
        "Number of players (even, >= 4)",
        default=_DEFAULT_PLAYERS,
        lo=1,
        hi=_MAX_PLAYERS,
        validate=_validate_players,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    num_decks = _ask_int_with_default(
        "Number of decks (even, >= 2)",
        default=_DEFAULT_DECKS,
        lo=1,
        hi=_MAX_DECKS,
        validate=_validate_decks,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    reserves = _ask_int_with_default(
        "Reserve hands per team (1 <= x <= decks)",
        default=min(_DEFAULT_RESERVES, num_decks),
        lo=1,
        hi=_MAX_DECKS,
        validate=_make_reserve_validator(num_decks),
        input_fn=input_fn,
        output_fn=output_fn,
    )

    names: list[str] = []
    for i in range(num_players):
        raw = input_fn(f"Player {i + 1} name: ")
        names.append(raw.strip() or f"Player{i + 1}")

    seed = _resolve_seed(output_fn=output_fn)
    config = GameConfig(
        num_players=num_players,
        num_decks=num_decks,
        reserves_per_team=reserves,
        seed=seed,
    )
    return config, names


def _ask_int_with_default(
    prompt: str,
    *,
    default: int,
    lo: int,
    hi: int,
    validate: Callable[[int], str | None],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> int:
    full_prompt = f"{prompt} [default {default}]: "
    while True:
        raw = input_fn(full_prompt)
        if not raw.strip():
            return default
        try:
            n = parse_int_in_range(raw, lo=lo, hi=hi)
        except BadInput as e:
            output_fn(f"  {e}. Try again.")
            continue
        err = validate(n)
        if err is None:
            return n
        output_fn(f"  {err}")


def _validate_players(n: int) -> str | None:
    if n < 4:
        return "Number of players must be at least 4 (two teams of 2)."
    if n % 2 != 0:
        return "Number of players must be even."
    return None


def _validate_decks(n: int) -> str | None:
    if n < 2:
        return "Need at least 2 decks."
    if n % 2 != 0:
        return "Number of decks must be even."
    return None


def _make_reserve_validator(num_decks: int) -> Callable[[int], str | None]:
    def _validate(n: int) -> str | None:
        if n < 1:
            return "Need at least 1 reserve hand per team."
        if n > num_decks:
            return f"Reserve hands per team cannot exceed number of decks ({num_decks})."
        return None

    return _validate


def _resolve_seed(*, output_fn: Callable[[str], None]) -> int:
    raw = os.environ.get("CANASTRA_SEED")
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            output_fn(f"  CANASTRA_SEED='{raw}' is not an integer; using a random seed.")
    return random.SystemRandom().randint(0, 2**31 - 1)
