"""Tests for RoomManager + Room dataclass — synchronous parts only."""

import pytest

from canastra.engine import GameConfig
from canastra.web.rooms import RoomManager, Unavailable


def _cfg(num_players=4):
    return GameConfig(num_players=num_players, num_decks=2, reserves_per_team=2, seed=42)


def test_create_returns_room_and_host_binding():
    mgr = RoomManager()
    room, host = mgr.create(host_nickname="Alice", config=_cfg())
    assert room.host_seat == 0
    assert host.nickname == "Alice"
    assert host.seat == 0
    assert room.code in mgr.rooms
    assert len(room.code) == 6


def test_join_allocates_next_seat():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    _, b1 = mgr.join(code=room.code, nickname="Bob")
    _, b2 = mgr.join(code=room.code, nickname="Carol")
    _, b3 = mgr.join(code=room.code, nickname="Dave")
    assert (b1.seat, b2.seat, b3.seat) == (1, 2, 3)


def test_join_rejects_full_room():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    for nick in ("Bob", "Carol", "Dave"):
        mgr.join(code=room.code, nickname=nick)
    with pytest.raises(Unavailable):
        mgr.join(code=room.code, nickname="Eve")


def test_join_rejects_unknown_room():
    mgr = RoomManager()
    with pytest.raises(Unavailable):
        mgr.join(code="ZZZZZZ", nickname="Bob")


def test_join_rejects_started_game():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    for nick in ("Bob", "Carol", "Dave"):
        mgr.join(code=room.code, nickname=nick)
    room.phase = "playing"
    with pytest.raises(Unavailable):
        mgr.join(code=room.code, nickname="Eve")


def test_nickname_regex_rejected():
    mgr = RoomManager()
    with pytest.raises(Unavailable):
        mgr.create(host_nickname="bad<name>", config=_cfg())
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    with pytest.raises(Unavailable):
        mgr.join(code=room.code, nickname="../etc/passwd")


def test_nickname_regex_accepts_alphanumeric_space_dash_apostrophe():
    mgr = RoomManager()
    for nick in ("Alice", "Bob 2", "O'Brien", "anne-marie", "Lu_cas"):
        room, _ = mgr.create(host_nickname=nick, config=_cfg())
        assert room.code in mgr.rooms


def test_get_returns_room_or_none():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    assert mgr.get(room.code) is room
    assert mgr.get("NOPENO") is None
