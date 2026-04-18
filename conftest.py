"""Phase-0 conftest: make the flat-layout modules importable from tests/.

The codebase is still a flat layout (`deck.py`, `player.py`, `table.py`,
`helpers.py`, `main.py` at repo root). `--import-mode=importlib` does not
automatically add the rootdir to `sys.path`, so `from deck import Card`
inside `tests/` would fail without this shim.

Delete this file once Phase 1 extracts `canastra/domain/` as a proper
installable package — at that point tests will import from `canastra.*`
and the shim becomes unnecessary.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
