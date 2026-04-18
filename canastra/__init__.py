"""Canastra — family-variant card game.

Layered package:
  - canastra.domain   — pure, side-effect-free rules, cards, scoring.
  - canastra.engine   — (Phase 2) deterministic state machine over domain.
  - canastra.service  — (Phase 4) HTTP/WS delivery + room management.

Nothing above the domain layer imports `random`, `input`, `print`, sockets,
or databases. Upper layers pass dependencies in explicitly.
"""

__version__ = "0.1.0"
