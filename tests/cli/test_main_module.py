"""Smoke test: `python -m canastra` launches the CLI."""

from __future__ import annotations

import subprocess
import sys


def test_python_m_canastra_runs_setup_then_exits() -> None:
    """Feed EOF on the first prompt — the CLI should exit cleanly with
    code 130 (EOF during setup)."""
    result = subprocess.run(
        [sys.executable, "-m", "canastra"],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 130
    assert "cancel" in result.stdout.lower() or "cancel" in result.stderr.lower()
