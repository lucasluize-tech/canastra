"""HTTP routes: room creation + lobby info + static index."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from canastra.engine import GameConfig
from canastra.web.rooms import RoomManager, Unavailable
from canastra.web.session import sign_cookie

router = APIRouter()

COOKIE_NAME = "canastra_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


class CreateRoomRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    num_players: int = Field(ge=2, le=32)
    num_decks: int = Field(ge=1, le=16)
    reserves_per_team: int = Field(ge=1, le=16)
    timer_enabled: bool = False
    team_mode: Literal["by_join_order", "by_choice"] = "by_join_order"
    host_team: int | None = Field(default=None, ge=0, le=1)


class CreateRoomResponse(BaseModel):
    room_code: str


def _manager(request: Request) -> RoomManager:
    return request.app.state.manager


def _secret(request: Request) -> bytes:
    return request.app.state.secret


def _set_session_cookie(response: Response, session_id: str, secret: bytes) -> None:
    blob = sign_cookie(session_id, secret)
    secure = os.environ.get("CANASTRA_DEBUG") != "1"
    response.set_cookie(
        key=COOKIE_NAME,
        value=blob,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _unavailable() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "unavailable"})


@router.post("/rooms", response_model=CreateRoomResponse)
async def post_rooms(
    body: CreateRoomRequest,
    response: Response,
    manager: Annotated[RoomManager, Depends(_manager)],
    secret: Annotated[bytes, Depends(_secret)],
) -> CreateRoomResponse:
    try:
        config = GameConfig(
            num_players=body.num_players,
            num_decks=body.num_decks,
            reserves_per_team=body.reserves_per_team,
            timer_enabled=body.timer_enabled,
            seed=int.from_bytes(os.urandom(8), "big"),
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="invalid_config") from exc

    try:
        room, binding = manager.create(
            host_nickname=body.nickname,
            config=config,
            team_mode=body.team_mode,
            host_team=body.host_team,
        )
    except Unavailable:
        # Most common case: by_choice mode without host_team — surface as 422 so
        # the client can re-render the form with a clearer message.
        if body.team_mode == "by_choice" and body.host_team is None:
            raise HTTPException(status_code=422, detail="host_team_required") from None
        return _unavailable()  # type: ignore[return-value]

    _set_session_cookie(response, binding.session_id, secret)
    return CreateRoomResponse(room_code=room.code)


class JoinRoomRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    team: int | None = Field(default=None, ge=0, le=1)


class JoinRoomResponse(BaseModel):
    seat: int


@router.post("/rooms/{code}", response_model=JoinRoomResponse)
async def post_room_join(
    code: str,
    body: JoinRoomRequest,
    response: Response,
    manager: Annotated[RoomManager, Depends(_manager)],
    secret: Annotated[bytes, Depends(_secret)],
) -> JoinRoomResponse:
    room = manager.get(code)
    if room is not None and room.team_mode == "by_choice" and body.team is None:
        raise HTTPException(status_code=422, detail="team_required")
    try:
        _, binding = manager.join(code=code, nickname=body.nickname, team=body.team)
    except Unavailable:
        return _unavailable()  # type: ignore[return-value]

    _set_session_cookie(response, binding.session_id, secret)
    return JoinRoomResponse(seat=binding.seat)


@router.get("/rooms/{code}")
async def get_room_public(
    code: str,
    manager: Annotated[RoomManager, Depends(_manager)],
) -> dict[str, Any]:
    room = manager.get(code)
    if room is None:
        return _unavailable()  # type: ignore[return-value]
    return {
        "code": room.code,
        "host_seat": room.host_seat,
        "phase": room.phase,
        "team_mode": room.team_mode,
        "seats": [
            {
                "seat": s,
                "nickname": b.nickname,
                "connected": b.ws is not None,
                "team": s % 2,
            }
            for s, b in sorted(room.seats.items())
        ],
        "config": room.config.model_dump(),
    }


@router.get("/")
async def index() -> Response:
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return Response(content="canastra (no static client built yet)", media_type="text/plain")
