"""WebSocket endpoint /ws/room/{code}."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from canastra.engine.errors import ActionRejected
from canastra.web.http_routes import COOKIE_MAX_AGE, COOKIE_NAME
from canastra.web.messages import (
    Accepted,
    ClientEnvelope,
    LeaveRoom,
    Ping,
    Pong,
    Rejected,
    Rematch,
    RequestSnapshot,
    ServerEnvelope,
    Snapshot,
    StartGame,
    SubmitAction,
    Welcome,
)
from canastra.web.rooms import Room, RoomManager, Unavailable
from canastra.web.session import SessionBinding, verify_cookie

log = logging.getLogger("canastra.web.ws")
router = APIRouter()


def _manager(ws: WebSocket) -> RoomManager:
    return ws.app.state.manager


def _secret(ws: WebSocket) -> bytes:
    return ws.app.state.secret


def _origin_allowed(origin: str | None) -> bool:
    # In debug mode, accept any origin (or no origin) — make web is localhost-only.
    if os.environ.get("CANASTRA_DEBUG") == "1":
        return True
    if origin is None:
        return False
    allowed = {
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://testserver",
    }
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
    origin = ws.headers.get("origin")
    if not _origin_allowed(origin):
        log.warning("WS rejected: origin=%r host=%r", origin, ws.headers.get("host"))
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

    if binding.seat == room.host_seat:
        room.cancel_lobby_grace()

    welcome = ServerEnvelope(
        v=1, msg=Welcome(type="welcome", seat=binding.seat, room=room.public_info())
    )
    await ws.send_text(welcome.model_dump_json())

    if room.phase == "lobby":
        await room.broadcast_lobby_update()
    else:
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
        if room.phase == "lobby" and binding.seat == room.host_seat:
            room.start_lobby_grace(timeout=60.0)


async def _close_old(ws: WebSocket) -> None:
    with contextlib.suppress(Exception):
        await asyncio.wait_for(ws.close(code=4000), timeout=1.0)


async def _handle_message(room: Room, binding: SessionBinding, raw: str) -> None:
    """Dispatch one WS message."""
    try:
        env = ClientEnvelope.model_validate_json(raw)
    except ValidationError:
        await _reject(binding, client_msg_id=None, reason="bad_message")
        return

    msg = env.msg

    # Idempotency replay
    if env.client_msg_id in binding.recent_results:
        return  # cached side-effects already delivered

    if isinstance(msg, Ping):
        await _handle_ping(binding, env.client_msg_id)
        return

    if isinstance(msg, RequestSnapshot):
        await _handle_request_snapshot(room, binding, env.client_msg_id)
        return

    if isinstance(msg, LeaveRoom):
        await _handle_leave_room(room, binding)
        return

    if isinstance(msg, Rematch):
        await _handle_rematch(room, binding, env.client_msg_id)
        return

    if isinstance(msg, StartGame):
        await _handle_start_game(room, binding, env.client_msg_id)
        return

    if isinstance(msg, SubmitAction):
        await _handle_submit_action(room, binding, env.client_msg_id, msg)
        return

    await _reject(binding, client_msg_id=env.client_msg_id, reason="bad_message")


async def _handle_start_game(room: Room, binding: SessionBinding, msg_id: UUID) -> None:
    if binding.seat != room.host_seat:
        await _reject(binding, client_msg_id=msg_id, reason="not_host")
        return
    try:
        room.start_game()
    except Unavailable:
        await _reject(binding, client_msg_id=msg_id, reason="wrong_lobby_phase")
        return

    room.start_timer_task()
    assert room.state is not None  # start_game() guarantees state is set

    # Send Snapshot(reason="started") to every connected seat
    coros = []
    for seat, b in sorted(room.seats.items()):
        if b.ws is None:
            continue
        view = room.state.view_for(seat)
        env = ServerEnvelope(
            v=1,
            msg=Snapshot(
                type="snapshot",
                reason="started",
                snapshot=view,
                action_seq=room.state.action_seq,
                deadline_ms=None,
            ),
        )
        coros.append(room._send(b, env))
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)
    binding.remember_result(msg_id, [])


async def _handle_submit_action(
    room: Room, binding: SessionBinding, msg_id: UUID, msg: SubmitAction
) -> None:
    if room.phase != "playing":
        await _reject(binding, client_msg_id=msg_id, reason="wrong_phase")
        return

    # Server overwrites the action's player_id with the session seat
    action = msg.action.model_copy(update={"player_id": binding.seat})

    try:
        events = room.submit(action)
    except ActionRejected:
        await _reject(binding, client_msg_id=msg_id, reason="illegal_action")
        return

    room.maybe_end_after_events(events)

    assert room.state is not None  # submit() requires state; phase == "playing" guarantees it
    action_seq = room.state.action_seq

    # Send Accepted to the actor
    accepted = ServerEnvelope(
        v=1,
        msg=Accepted(type="accepted", client_msg_id=msg_id, action_seq=action_seq),
    )
    if binding.ws is not None:
        with contextlib.suppress(Exception):
            await binding.ws.send_text(accepted.model_dump_json())

    # Fanout events to all connected seats
    await room.fanout(events, action_seq=action_seq)
    binding.remember_result(msg_id, events)


async def _handle_ping(binding: SessionBinding, msg_id: UUID) -> None:
    if binding.ws is None:
        return
    pong = ServerEnvelope(
        v=1,
        msg=Pong(
            type="pong",
            client_msg_id=msg_id,
            server_time_ms=int(time.time() * 1000),
        ),
    )
    with contextlib.suppress(Exception):
        await binding.ws.send_text(pong.model_dump_json())


async def _handle_request_snapshot(room: Room, binding: SessionBinding, msg_id: UUID) -> None:
    if room.state is None:
        await _reject(binding, client_msg_id=msg_id, reason="wrong_phase")
        return
    assert room.state is not None
    view = room.state.view_for(binding.seat)
    env = ServerEnvelope(
        v=1,
        msg=Snapshot(
            type="snapshot",
            reason="requested",
            snapshot=view,
            action_seq=room.state.action_seq,
            deadline_ms=None,
        ),
    )
    with contextlib.suppress(Exception):
        if binding.ws is not None:
            await binding.ws.send_text(env.model_dump_json())
    binding.remember_result(msg_id, [])


async def _handle_leave_room(room: Room, binding: SessionBinding) -> None:
    """Player explicitly leaves. In lobby, free the seat; mid-game, keep the seat
    but mark them disconnected so turns still advance correctly."""
    if room.phase == "lobby":
        room.seats.pop(binding.seat, None)
    ws = binding.ws
    binding.ws = None
    if ws is not None:
        with contextlib.suppress(Exception):
            await ws.close(code=1000)


async def _handle_rematch(room: Room, binding: SessionBinding, msg_id: UUID) -> None:
    if binding.seat != room.host_seat:
        await _reject(binding, client_msg_id=msg_id, reason="not_host")
        return
    try:
        room.rematch()
    except Unavailable:
        await _reject(binding, client_msg_id=msg_id, reason="wrong_lobby_phase")
        return
    room.start_timer_task()
    assert room.state is not None
    coros = []
    for seat, b in sorted(room.seats.items()):
        if b.ws is None:
            continue
        view = room.state.view_for(seat)
        env = ServerEnvelope(
            v=1,
            msg=Snapshot(
                type="snapshot",
                reason="started",
                snapshot=view,
                action_seq=room.state.action_seq,
                deadline_ms=None,
            ),
        )
        coros.append(room._send(b, env))
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)
    binding.remember_result(msg_id, [])


RejectReason = Literal[
    "illegal_action",
    "not_your_turn",
    "wrong_phase",
    "unknown_room",
    "bad_message",
    "rate_limited",
    "unsupported_version",
    "not_host",
    "wrong_lobby_phase",
]


async def _reject(
    binding: SessionBinding,
    *,
    client_msg_id: UUID | None,
    reason: RejectReason,
) -> None:
    if binding.ws is None:
        return
    if client_msg_id is None:
        client_msg_id = uuid4()
    rejected = Rejected(type="rejected", client_msg_id=client_msg_id, reason=reason)
    env = ServerEnvelope(v=1, msg=rejected)
    with contextlib.suppress(Exception):
        await binding.ws.send_text(env.model_dump_json())
    binding.remember_result(client_msg_id, rejected)
