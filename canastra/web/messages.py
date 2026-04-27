"""WebSocket envelope and message types for the Phase 4 protocol.

All messages are pydantic v2 models. Client→server and server→client envelopes both
carry `v: 1`. The inner `msg` field is a discriminated union keyed on `type`.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from canastra.engine.actions import Action
from canastra.engine.events import Event
from canastra.engine.state import GameConfig, PlayerView

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


# ---------- Server → Client ----------


class SeatInfo(BaseModel):
    seat: int
    nickname: str
    connected: bool


class RoomPublic(BaseModel):
    code: str
    host_seat: int
    config: GameConfig
    phase: Literal["lobby", "playing", "ended"]
    seats: list[SeatInfo]


class Welcome(BaseModel):
    type: Literal["welcome"] = "welcome"
    seat: int
    room: RoomPublic


class LobbyUpdate(BaseModel):
    type: Literal["lobby_update"] = "lobby_update"
    seats: list[SeatInfo]


class Snapshot(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    reason: Literal["started", "reconnect", "requested"]
    snapshot: PlayerView
    action_seq: int
    deadline_ms: int | None = None


class EventMsg(BaseModel):
    type: Literal["event"] = "event"
    event: Event
    action_seq: int


class Accepted(BaseModel):
    type: Literal["accepted"] = "accepted"
    client_msg_id: UUID
    action_seq: int


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


class DeadlineWarning(BaseModel):
    type: Literal["deadline_warning"] = "deadline_warning"
    deadline_ms: int


class RoomClosed(BaseModel):
    type: Literal["room_closed"] = "room_closed"
    reason: Literal["host_left", "empty", "server_shutdown"]


class Heartbeat(BaseModel):
    type: Literal["heartbeat"] = "heartbeat"
    server_time_ms: int


class Pong(BaseModel):
    type: Literal["pong"] = "pong"
    client_msg_id: UUID
    server_time_ms: int


ServerMsg = Annotated[
    Welcome
    | LobbyUpdate
    | Snapshot
    | EventMsg
    | Accepted
    | Rejected
    | DeadlineWarning
    | RoomClosed
    | Heartbeat
    | Pong,
    Field(discriminator="type"),
]


class ServerEnvelope(BaseModel):
    v: Literal[1]
    msg: ServerMsg


__all__ = [
    "Accepted",
    "ClientEnvelope",
    "ClientMsg",
    "DeadlineWarning",
    "EventMsg",
    "Heartbeat",
    "LeaveRoom",
    "LobbyUpdate",
    "Ping",
    "Pong",
    "Rejected",
    "Rematch",
    "RequestSnapshot",
    "RoomClosed",
    "RoomPublic",
    "SeatInfo",
    "ServerEnvelope",
    "ServerMsg",
    "Snapshot",
    "StartGame",
    "SubmitAction",
    "Welcome",
]
