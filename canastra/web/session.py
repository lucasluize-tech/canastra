"""Session bindings, in-memory store, and signed-cookie helpers."""

from __future__ import annotations

import asyncio
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

if TYPE_CHECKING:
    from fastapi import WebSocket

    from canastra.engine.events import Event
    from canastra.web.messages import Rejected


SessionId = str
PlayerId = int

_SERIALIZER_SALT = "canastra.session.v1"
_RECENT_RESULTS_MAX = 64


def new_session_id() -> SessionId:
    """Return a fresh, unguessable session id."""
    return secrets.token_urlsafe(32)


def _serializer(secret: bytes) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt=_SERIALIZER_SALT)


def sign_cookie(session_id: SessionId, secret: bytes) -> str:
    """Return a URL-safe, HMAC-signed, timestamped cookie blob."""
    return _serializer(secret).dumps(session_id)


def verify_cookie(blob: str, secret: bytes, max_age: int) -> SessionId | None:
    """Return the session_id if the cookie verifies; else None.

    itsdangerous uses constant-time HMAC comparison internally.
    """
    try:
        loaded = _serializer(secret).loads(blob, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(loaded, str):
        return None
    return loaded


@dataclass
class SessionBinding:
    """Live state for one player's session.

    Plain dataclass (not pydantic) — holds asyncio primitives.
    """

    session_id: SessionId
    room_code: str
    seat: PlayerId
    nickname: str
    created_at: datetime
    ws: WebSocket | None = None
    ws_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    recent_results: OrderedDict[UUID, list[Event] | Rejected] = field(default_factory=OrderedDict)

    def remember_result(self, msg_id: UUID, result: list[Event] | Rejected) -> None:
        """Store a per-session result, bounded to the most recent 64 entries."""
        self.recent_results[msg_id] = result
        while len(self.recent_results) > _RECENT_RESULTS_MAX:
            self.recent_results.popitem(last=False)


class SessionStore:
    """In-memory map of session_id -> SessionBinding."""

    def __init__(self) -> None:
        self._bindings: dict[SessionId, SessionBinding] = {}

    def new(self, *, room_code: str, seat: PlayerId, nickname: str) -> SessionBinding:
        binding = SessionBinding(
            session_id=new_session_id(),
            room_code=room_code,
            seat=seat,
            nickname=nickname,
            created_at=datetime.now(UTC),
        )
        self._bindings[binding.session_id] = binding
        return binding

    def get(self, session_id: SessionId) -> SessionBinding | None:
        return self._bindings.get(session_id)

    def revoke(self, session_id: SessionId) -> None:
        self._bindings.pop(session_id, None)

    def all_for_room(self, room_code: str) -> list[SessionBinding]:
        return [b for b in self._bindings.values() if b.room_code == room_code]


__all__ = [
    "PlayerId",
    "SessionBinding",
    "SessionId",
    "SessionStore",
    "new_session_id",
    "sign_cookie",
    "verify_cookie",
]
