"""Room state, RoomManager, and the synchronous read-modify-write submit path.

Async parts (fanout, AFK timer, lobby grace) are layered on top in later tasks.
"""

from __future__ import annotations

import asyncio
import random
import re
from dataclasses import dataclass, field
from typing import Literal

from canastra.engine import GameConfig, GameState
from canastra.web.codes import generate_room_code
from canastra.web.session import SessionBinding, SessionStore

NICKNAME_RE = re.compile(r"^[\w \-']{1,20}$")


class Unavailable(Exception):
    """Single sentinel for "no such room / full / started / invalid nickname"."""


@dataclass
class Room:
    code: str
    config: GameConfig
    host_seat: int
    seats: dict[int, SessionBinding]
    state: GameState | None = None
    phase: Literal["lobby", "playing", "ended"] = "lobby"
    timer_task: asyncio.Task[None] | None = None
    deadline_changed: asyncio.Event = field(default_factory=asyncio.Event)
    _lobby_grace_task: asyncio.Task[None] | None = None
    _closed: bool = False
    _rng: random.Random = field(default_factory=random.Random)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.sessions = SessionStore()
        self._sysrng = random.SystemRandom()

    def _generate_unique_code(self) -> str:
        for _ in range(8):
            code = generate_room_code(self._sysrng)
            if code not in self.rooms:
                return code
        raise Unavailable

    def _validate_nickname(self, nickname: str) -> None:
        if not NICKNAME_RE.match(nickname):
            raise Unavailable

    def create(self, *, host_nickname: str, config: GameConfig) -> tuple[Room, SessionBinding]:
        self._validate_nickname(host_nickname)
        code = self._generate_unique_code()
        binding = self.sessions.new(room_code=code, seat=0, nickname=host_nickname)
        room = Room(
            code=code,
            config=config,
            host_seat=0,
            seats={0: binding},
            _rng=random.Random(config.seed),
        )
        self.rooms[code] = room
        return room, binding

    def join(self, *, code: str, nickname: str) -> tuple[Room, SessionBinding]:
        self._validate_nickname(nickname)
        room = self.rooms.get(code)
        if room is None or room.phase != "lobby":
            raise Unavailable
        if len(room.seats) >= room.config.num_players:
            raise Unavailable
        next_seat = max(room.seats) + 1
        binding = self.sessions.new(room_code=code, seat=next_seat, nickname=nickname)
        room.seats[next_seat] = binding
        return room, binding

    def get(self, code: str) -> Room | None:
        return self.rooms.get(code)
