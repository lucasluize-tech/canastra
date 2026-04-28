"""Tests for RoomManager + Room dataclass — synchronous parts only."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from canastra.domain.cards import HEARTS, Card
from canastra.engine import GameConfig, initial_state
from canastra.engine.actions import Draw
from canastra.engine.events import CardDrawn, TurnAdvanced
from canastra.web.rooms import Room, RoomManager, Unavailable


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


def test_submit_advances_state_and_returns_events():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    for nick in ("Bob", "Carol", "Dave"):
        mgr.join(code=room.code, nickname=nick)
    room.phase = "playing"
    room.state = initial_state(room.config)

    initial_seq = room.state.action_seq
    events = room.submit(Draw(player_id=room.state.current_turn.player_id))
    assert events
    assert room.state.action_seq == initial_seq + 1


def test_submit_is_synchronous():
    """Compile-time guard: Room.submit must not be a coroutine."""
    assert not inspect.iscoroutinefunction(Room.submit)


def test_recent_results_remembers_idempotently():
    """SessionBinding.remember_result keeps the cache bounded to 64."""
    mgr = RoomManager()
    _, host = mgr.create(host_nickname="Alice", config=_cfg())
    for _i in range(70):
        host.remember_result(uuid4(), [])
    assert len(host.recent_results) == 64


# ---------------------------------------------------------------------------
# Async tests for Room.fanout + _send + _mark_dead (Task 13)
# ---------------------------------------------------------------------------


def _room_with_4_seats() -> Room:
    """Return a Room with 4 seats, each having a fresh MagicMock WebSocket."""
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    for nick in ("Bob", "Carol", "Dave"):
        mgr.join(code=room.code, nickname=nick)
    # Attach a mock WebSocket to every binding
    for binding in room.seats.values():
        ws = MagicMock()
        ws.send_text = AsyncMock()
        binding.ws = ws
    return room


@pytest.mark.asyncio
async def test_fanout_audience_filter_public_event_goes_to_everyone():
    """A public event (audience=None) should be sent to all 4 seats."""
    room = _room_with_4_seats()
    ev = TurnAdvanced(next_player_id=1)  # audience defaults to None
    assert ev.audience is None

    await room.fanout([ev], action_seq=11)

    for binding in room.seats.values():
        binding.ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_fanout_private_event_goes_only_to_audience():
    """A private event (audience=2) should only reach seat 2."""
    room = _room_with_4_seats()
    card = Card(suit=HEARTS, rank="Ace")
    ev = CardDrawn(player_id=2, card=card, audience=2)
    assert ev.audience == 2

    await room.fanout([ev], action_seq=6)

    # Only seat 2 should have received the message
    room.seats[2].ws.send_text.assert_called_once()
    for seat, binding in room.seats.items():
        if seat != 2:
            binding.ws.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_fanout_drops_slow_client():
    """A seat whose send_text hangs past _send_timeout is marked dead (ws=None).

    Other seats must still receive the message and the test must complete well
    under the hang duration (5 s).
    """
    room = _room_with_4_seats()

    # Make seat 1 hang forever
    async def _hang(*_args, **_kwargs):
        await asyncio.sleep(5)

    room.seats[1].ws.send_text = _hang
    slow_binding = room.seats[1]

    ev = TurnAdvanced(next_player_id=2)
    await room.fanout([ev], action_seq=1, _send_timeout=0.1)

    # Slow seat must be marked dead
    assert slow_binding.ws is None

    # All other seats must have received the message
    for seat, binding in room.seats.items():
        if seat != 1:
            binding.ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_fanout_assigns_same_action_seq_to_all_events_from_one_submit():
    """All events from one submit() share the same action_seq.

    Engine bumps state.action_seq by 1 per action regardless of event count,
    so a Discard producing (Discarded, TurnAdvanced) must broadcast both with
    the same seq — otherwise client gap detection breaks on reconnect.
    """
    room = _room_with_4_seats()
    events = [TurnAdvanced(next_player_id=1), TurnAdvanced(next_player_id=2)]

    await room.fanout(events, action_seq=42)

    # Each seat should have received both events, both at seq=42
    for binding in room.seats.values():
        assert binding.ws.send_text.call_count == 2
        for call in binding.ws.send_text.call_args_list:
            blob = call.args[0]
            assert '"action_seq":42' in blob
