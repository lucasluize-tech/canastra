"""Lifespan shutdown tears down rooms cleanly."""

import pytest
from fastapi.testclient import TestClient

from canastra.web.app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("CANASTRA_DEBUG", "1")
    return create_app(debug=False)


def test_shutdown_clears_rooms(app):
    """After lifespan exit, RoomManager.rooms is empty."""
    with TestClient(app) as client:
        client.post(
            "/rooms",
            json={
                "nickname": "Alice",
                "num_players": 4,
                "num_decks": 2,
                "reserves_per_team": 2,
                "timer_enabled": False,
            },
        )
        assert len(app.state.manager.rooms) == 1
    # After context-exit, lifespan shutdown ran via _shutdown_manager.
    assert len(app.state.manager.rooms) == 0
