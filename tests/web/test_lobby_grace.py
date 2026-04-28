"""When the host disconnects in lobby, a grace task starts. Reconnect cancels it."""

import asyncio

import pytest

from canastra.engine import GameConfig
from canastra.web.rooms import RoomManager


def _cfg():
    return GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=1)


@pytest.mark.asyncio
async def test_lobby_grace_cancelled_on_host_reconnect():
    mgr = RoomManager()
    room, host = mgr.create(host_nickname="Alice", config=_cfg())
    room.start_lobby_grace(timeout=60.0)
    assert room._lobby_grace_task is not None
    assert not room._lobby_grace_task.done()

    room.cancel_lobby_grace()
    assert room._lobby_grace_task is None or room._lobby_grace_task.cancelled()


@pytest.mark.asyncio
async def test_lobby_grace_fires_after_timeout():
    mgr = RoomManager()
    room, _ = mgr.create(host_nickname="Alice", config=_cfg())
    room.start_lobby_grace(timeout=0.1)
    await asyncio.sleep(0.3)
    assert room._closed
