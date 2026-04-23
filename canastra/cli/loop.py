"""Top-level CLI game loop (stub — filled in by later tasks)."""

from __future__ import annotations

from collections.abc import Callable


def run(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Run an interactive Canastra game to completion.

    Returns a Unix-style exit code: 0 on normal completion, 130 on
    KeyboardInterrupt/EOF.
    """
    raise NotImplementedError("filled in by Task 11")
