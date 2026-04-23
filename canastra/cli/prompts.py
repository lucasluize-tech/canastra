"""CLI input parsing.

Pure `parse_*` helpers do only structural validation (is this a number,
is it in range, is it one of these choices). They raise BadInput on
failure. The `ask_*` wrappers (added in Task 3) turn those exceptions
into reprompt loops against an injected input function.

Rule validation lives in the engine, not here — this module has no
knowledge of whose turn it is, which melds exist, or which moves are
legal.
"""

from __future__ import annotations

from collections.abc import Callable


class BadInput(Exception):
    """Raised by parse_* helpers when input is structurally invalid."""


def parse_card_indices(raw: str, hand_size: int) -> list[int]:
    """Parse a comma-separated list of 1-based card indices.

    Preserves input order. Rejects empty input, non-integers, zero,
    out-of-range values, and duplicates.
    """
    if not raw or not raw.strip():
        raise BadInput("no cards selected")
    parts = [p.strip() for p in raw.split(",")]
    result: list[int] = []
    for p in parts:
        if not p.lstrip("-").isdigit():
            raise BadInput(f"'{p}' is not a number")
        n = int(p)
        if n < 1:
            raise BadInput(f"index must be >= 1 (got {n})")
        if n > hand_size:
            raise BadInput(f"index {n} exceeds hand size {hand_size}")
        if n in result:
            raise BadInput(f"index {n} selected twice")
        result.append(n)
    return result


def parse_yes_no(raw: str) -> bool:
    """Parse y/yes/n/no (case-insensitive). Raise BadInput otherwise."""
    s = raw.strip().lower()
    if s in {"y", "yes"}:
        return True
    if s in {"n", "no"}:
        return False
    raise BadInput(f"expected y/n, got '{raw}'")


def parse_choice(raw: str, options: set[str]) -> str:
    """Parse a single-letter/token choice (case-insensitive)."""
    s = raw.strip().lower()
    if s in options:
        return s
    raise BadInput(f"expected one of {sorted(options)}, got '{raw}'")


def parse_int_in_range(raw: str, lo: int, hi: int) -> int:
    """Parse an integer and verify lo <= n <= hi."""
    s = raw.strip()
    if not s.lstrip("-").isdigit():
        raise BadInput(f"'{raw}' is not a number")
    n = int(s)
    if n < lo or n > hi:
        raise BadInput(f"expected integer in [{lo}, {hi}], got {n}")
    return n


def _reprompt_loop(
    prompt: str,
    parse: Callable[[str], object],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> object:
    """Common reprompt loop: call input_fn, parse, print error on BadInput."""
    while True:
        raw = input_fn(prompt)
        try:
            return parse(raw)
        except BadInput as e:
            output_fn(f"  {e}. Try again.")


def ask_choice(
    prompt: str,
    options: set[str],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> str:
    return _reprompt_loop(prompt, lambda raw: parse_choice(raw, options), input_fn, output_fn)  # type: ignore[return-value]


def ask_yes_no(
    prompt: str,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    return _reprompt_loop(prompt, parse_yes_no, input_fn, output_fn)  # type: ignore[return-value]


def ask_int_in_range(
    prompt: str,
    lo: int,
    hi: int,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    return _reprompt_loop(prompt, lambda raw: parse_int_in_range(raw, lo, hi), input_fn, output_fn)  # type: ignore[return-value]


def ask_card_indices(
    prompt: str,
    hand_size: int,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> list[int]:
    return _reprompt_loop(
        prompt, lambda raw: parse_card_indices(raw, hand_size), input_fn, output_fn
    )  # type: ignore[return-value]
