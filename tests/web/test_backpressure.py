"""A slow sender does not block the room. Slow client gets dropped."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from canastra.engine import GameConfig
from canastra.engine.events import TurnAdvanced
from canastra.web.rooms import RoomManager


@pytest.mark.asyncio
async def test_slow_client_dropped_after_send_timeout():
    mgr = RoomManager()
    room, _ = mgr.create(
        host_nickname="Alice",
        config=GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=1),
    )
    for nick in ("Bob", "Carol", "Dave"):
        mgr.join(code=room.code, nickname=nick)

    fast_seats = (0, 2, 3)
    slow_seat = 1

    for s in fast_seats:
        room.seats[s].ws = MagicMock()
        room.seats[s].ws.send_text = AsyncMock()

    async def hang(_):
        await asyncio.sleep(5)

    slow_ws = MagicMock()
    slow_ws.send_text = AsyncMock(side_effect=hang)
    slow_ws.close = AsyncMock()
    room.seats[slow_seat].ws = slow_ws

    await room.fanout([TurnAdvanced(next_player_id=0)], action_seq=0, _send_timeout=0.05)

    assert room.seats[slow_seat].ws is None
    for s in fast_seats:
        room.seats[s].ws.send_text.assert_called_once()
