"""WebSocket envelope and message types for the Phase 4 protocol.

All messages are pydantic v2 models. Client→server and server→client envelopes both
carry `v: 1`. The inner `msg` field is a discriminated union keyed on `type`.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from canastra.engine.actions import Action

# ---------- Client → Server ----------


class StartGame(BaseModel):
    type: Literal["start_game"] = "start_game"


class SubmitAction(BaseModel):
    type: Literal["submit_action"] = "submit_action"
    action: Action


class Rematch(BaseModel):
    type: Literal["rematch"] = "rematch"


class LeaveRoom(BaseModel):
    type: Literal["leave_room"] = "leave_room"


class RequestSnapshot(BaseModel):
    type: Literal["request_snapshot"] = "request_snapshot"


class Ping(BaseModel):
    type: Literal["ping"] = "ping"


ClientMsg = Annotated[
    StartGame | SubmitAction | Rematch | LeaveRoom | RequestSnapshot | Ping,
    Field(discriminator="type"),
]


class ClientEnvelope(BaseModel):
    v: Literal[1]
    client_msg_id: UUID
    msg: ClientMsg


# ---------- Server → Client (partial — only Rejected needed by session.py) ----------


class Rejected(BaseModel):
    """Server rejection message for a client action."""

    type: Literal["rejected"] = "rejected"
    client_msg_id: UUID
    reason: Literal[
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
    detail: str | None = None


__all__ = [
    "ClientEnvelope",
    "ClientMsg",
    "LeaveRoom",
    "Ping",
    "Rejected",
    "Rematch",
    "RequestSnapshot",
    "StartGame",
    "SubmitAction",
]
