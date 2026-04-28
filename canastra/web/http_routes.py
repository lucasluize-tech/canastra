"""HTTP routes: room creation + lobby info + static index."""

from __future__ import annotations

import os
from typing import Annotated

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
        room, binding = manager.create(host_nickname=body.nickname, config=config)
    except Unavailable:
        return _unavailable()  # type: ignore[return-value]

    _set_session_cookie(response, binding.session_id, secret)
    return CreateRoomResponse(room_code=room.code)


@router.get("/")
async def index() -> Response:
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return Response(content="canastra (no static client built yet)", media_type="text/plain")
