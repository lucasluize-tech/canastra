"""FastAPI app factory with lifespan-managed RoomManager."""

from __future__ import annotations

import asyncio
import contextlib
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from canastra.web.messages import RoomClosed, ServerEnvelope
from canastra.web.rooms import RoomManager


def create_app(*, debug: bool = False) -> FastAPI:
    secret = os.environ.get("CANASTRA_SESSION_SECRET")
    if not debug:
        assert secret and len(secret) >= 32, (
            "CANASTRA_SESSION_SECRET unset or too short (need >= 32 bytes)"
        )
        assert os.environ.get("WEB_CONCURRENCY", "1") == "1", (
            "Phase 4 requires uvicorn --workers 1; multi-worker silently partitions rooms"
        )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.manager = RoomManager()
        app.state.secret = (secret or "debug-secret-debug-secret-debug-").encode("utf-8")
        try:
            yield
        finally:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(_shutdown_manager(app.state.manager), timeout=5.0)

    fastapi_app = FastAPI(lifespan=lifespan)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        fastapi_app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return fastapi_app


async def _shutdown_manager(manager: RoomManager) -> None:
    """Cancel timer tasks, broadcast RoomClosed(server_shutdown), close sockets, drop rooms."""
    rooms = list(manager.rooms.values())

    # Cancel all background tasks first
    for room in rooms:
        if room.timer_task is not None:
            room.timer_task.cancel()
        if room._lobby_grace_task is not None:
            room._lobby_grace_task.cancel()

    # Await cancellation (swallow CancelledError and any other exception)
    tasks = [r.timer_task for r in rooms if r.timer_task] + [
        r._lobby_grace_task for r in rooms if r._lobby_grace_task
    ]
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    # Broadcast RoomClosed then close each socket with code 1001 (going away)
    env = ServerEnvelope(v=1, msg=RoomClosed(type="room_closed", reason="server_shutdown"))
    blob = env.model_dump_json()
    for room in rooms:
        for binding in list(room.seats.values()):
            ws = binding.ws
            if ws is None:
                continue
            with contextlib.suppress(Exception):
                await asyncio.wait_for(ws.send_text(blob), timeout=0.5)
            with contextlib.suppress(Exception):
                await ws.close(code=1001)
        room._closed = True

    manager.rooms.clear()


app = create_app(debug=os.environ.get("CANASTRA_DEBUG") == "1")
