"""HTTP route tests — POST /rooms, GET /."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canastra.web.app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    app = create_app(debug=False)
    with TestClient(app) as c:
        yield c


def test_post_rooms_creates_and_sets_cookie(client):
    resp = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "room_code" in body
    assert len(body["room_code"]) == 6
    assert any(c.lower().startswith("canastra_session=") for c in resp.headers.get_list("set-cookie"))


def test_post_rooms_rejects_bad_nickname(client):
    resp = client.post(
        "/rooms",
        json={
            "nickname": "<script>",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
        },
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "unavailable"}


def test_post_rooms_rejects_bad_config(client):
    resp = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 3,  # must be even, and also < 4 minimum
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
        },
    )
    assert resp.status_code == 422
