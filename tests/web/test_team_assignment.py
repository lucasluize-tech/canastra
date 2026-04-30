"""Team-assignment policy: by_join_order (default) vs by_choice."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from canastra.engine import GameConfig
from canastra.web.app import create_app
from canastra.web.rooms import RoomManager, Unavailable

# ---------------------------------------------------------------------------
# Direct RoomManager tests — engine-free, no HTTP layer.
# ---------------------------------------------------------------------------


def _cfg() -> GameConfig:
    return GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=1)


def test_by_join_order_assigns_seats_sequentially():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    assert room.team_mode == "by_join_order"
    assert room.host_seat == 0
    for nick, expected_seat in [("Bob", 1), ("Carol", 2), ("Dave", 3)]:
        _, b = mgr.join(code=room.code, nickname=nick)
        assert b.seat == expected_seat


def test_by_choice_host_team_0_takes_seat_0():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice", host_team=0)
    assert room.team_mode == "by_choice"
    assert room.host_seat == 0


def test_by_choice_host_team_1_takes_seat_1():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice", host_team=1)
    assert room.host_seat == 1
    # Seat 0 is still free for a team-0 joiner.
    _, b = mgr.join(code=room.code, nickname="Bob", team=0)
    assert b.seat == 0


def test_by_choice_requires_host_team():
    mgr = RoomManager()
    with pytest.raises(Unavailable):
        mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice")


def test_by_choice_join_requires_team():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice", host_team=0)
    with pytest.raises(Unavailable):
        mgr.join(code=room.code, nickname="Bob")  # missing team


def test_by_choice_team_full_raises_unavailable():
    """Host team=0 + 2 more team-0 joiners (host filled seat 0; need only one more)
    means seat 2 is the only remaining team-0 slot. A 3rd team-0 join must fail."""
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice", host_team=0)
    # Bob takes the other team-0 seat (seat 2).
    _, b = mgr.join(code=room.code, nickname="Bob", team=0)
    assert b.seat == 2
    # Carol attempts team-0 but both seats are now full.
    with pytest.raises(Unavailable):
        mgr.join(code=room.code, nickname="Carol", team=0)


def test_by_choice_full_4p_balanced_assignment():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg(), team_mode="by_choice", host_team=0)
    _, b1 = mgr.join(code=room.code, nickname="Bob", team=1)
    _, c = mgr.join(code=room.code, nickname="Carol", team=0)
    _, d = mgr.join(code=room.code, nickname="Dave", team=1)
    assert (b1.seat, c.seat, d.seat) == (1, 2, 3)
    assert sorted(room.seats) == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# HTTP layer tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    app = create_app(debug=False)
    with TestClient(app) as c:
        yield c


def test_post_rooms_by_choice_without_host_team_returns_422(client):
    resp = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
            "team_mode": "by_choice",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "host_team_required"


def test_post_rooms_by_choice_with_host_team_succeeds(client):
    resp = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
            "team_mode": "by_choice",
            "host_team": 1,
        },
    )
    assert resp.status_code == 200


def test_join_by_choice_without_team_returns_422(client):
    create = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
            "team_mode": "by_choice",
            "host_team": 0,
        },
    )
    code = create.json()["room_code"]
    resp = client.post(f"/rooms/{code}", json={"nickname": "Bob"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "team_required"


def test_get_room_exposes_team_mode_and_seat_team(client):
    create = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
            "team_mode": "by_choice",
            "host_team": 1,
        },
    )
    code = create.json()["room_code"]
    info = client.get(f"/rooms/{code}").json()
    assert info["team_mode"] == "by_choice"
    assert info["host_seat"] == 1
    assert info["seats"][0] == {
        "seat": 1,
        "nickname": "Alice",
        "connected": False,
        "team": 1,
    }


def test_get_room_default_mode_is_by_join_order(client):
    create = client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
        },
    )
    code = create.json()["room_code"]
    info = client.get(f"/rooms/{code}").json()
    assert info["team_mode"] == "by_join_order"
