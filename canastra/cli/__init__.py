"""Canastra terminal CLI — Phase 3.

This is the delivery layer above the game engine. It translates
stdin/stdout into engine Actions and engine Events, and nothing else.
All rules and state transitions live in canastra.engine.
"""

from canastra.cli.loop import run

__all__ = ["run"]
