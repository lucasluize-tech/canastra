"""WebSocket endpoint /ws/room/{code}."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from canastra.web.http_routes import COOKIE_MAX_AGE, COOKIE_NAME
from canastra.web.messages import (
    ServerEnvelope,
    Welcome,
)
from canastra.web.rooms import Room, RoomManager
from canastra.web.session import SessionBinding, verify_cookie

router = APIRouter()


def _manager(ws: WebSocket) -> RoomManager:
    return ws.app.state.manager


def _secret(ws: WebSocket) -> bytes:
    return ws.app.state.secret


def _origin_allowed(origin: str | None) -> bool:
    if origin is None:
        return False
    allowed = {"http://localhost", "http://localhost:8000", "http://testserver"}
    public = os.environ.get("CANASTRA_PUBLIC_HOST")
    if public:
        allowed.add(f"https://{public}")
        allowed.add(f"http://{public}")
    # Allow exact-prefix match (host:port may vary)
    return any(
        origin == a or origin.startswith(a + ":") or origin.startswith(a + "/") for a in allowed
    )


@router.websocket("/ws/room/{code}")
async def ws_room(
    ws: WebSocket,
    code: str,
    manager: Annotated[RoomManager, Depends(_manager)],
    secret: Annotated[bytes, Depends(_secret)],
):
    if not _origin_allowed(ws.headers.get("origin")):
        await ws.close(code=4403)
        return

    cookie_blob = ws.cookies.get(COOKIE_NAME)
    if not cookie_blob:
        await ws.close(code=1008)
        return
    session_id = verify_cookie(cookie_blob, secret, max_age=COOKIE_MAX_AGE)
    if session_id is None:
        await ws.close(code=1008)
        return

    binding = manager.sessions.get(session_id)
    if binding is None or binding.room_code != code:
        await ws.close(code=1008)
        return

    room = manager.get(code)
    if room is None:
        await ws.close(code=1011)
        return

    await ws.accept()

    async with binding.ws_lock:
        old = binding.ws
        binding.ws = ws
        if old is not None and old is not ws:
            asyncio.create_task(_close_old(old))

    welcome = ServerEnvelope(
        v=1, msg=Welcome(type="welcome", seat=binding.seat, room=room.public_info())
    )
    await ws.send_text(welcome.model_dump_json())

    if room.phase == "lobby":
        await room.broadcast_lobby_update()
    else:
        from canastra.web.messages import Snapshot

        assert room.state is not None  # phase != "lobby" implies state is initialized
        view = room.state.view_for(binding.seat)
        snap = ServerEnvelope(
            v=1,
            msg=Snapshot(
                type="snapshot",
                reason="reconnect",
                snapshot=view,
                action_seq=room.state.action_seq,
                deadline_ms=None,
            ),
        )
        await ws.send_text(snap.model_dump_json())

    try:
        async for raw in ws.iter_text():
            await _handle_message(room, binding, raw)
    except WebSocketDisconnect:
        pass
    finally:
        async with binding.ws_lock:
            if binding.ws is ws:
                binding.ws = None
        if room.phase == "lobby":
            await room.broadcast_lobby_update()


async def _close_old(ws: WebSocket) -> None:
    import contextlib

    with contextlib.suppress(Exception):
        await asyncio.wait_for(ws.close(code=4000), timeout=1.0)


async def _handle_message(room: Room, binding: SessionBinding, raw: str) -> None:
    """Dispatch one WS message — stub. Filled in in later tasks."""
    return None
