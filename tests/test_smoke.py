"""Import-time smoke test for the flat-layout modules.

Guards against regressions where a module fails to import at all — which
silently breaks every other test and every entry-point. `main.py` is
intentionally excluded: its module scope runs the interactive game loop
and calls `input()`, so importing it would hang the test run.

Delete or rewrite once Phase 1 moves the domain into `canastra/`.
"""

from __future__ import annotations

import importlib


def test_flat_modules_import() -> None:
    for name in ("deck", "player", "table", "helpers"):
        importlib.import_module(name)
