"""Room state, RoomManager, and the synchronous read-modify-write submit path.

Async parts (fanout, AFK timer, lobby grace) are layered on top in later tasks.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import re
from dataclasses import dataclass, field
from typing import Literal

from canastra.engine import (
    GameConfig,
    GameState,
    apply,
)
from canastra.engine.actions import Action
from canastra.engine.events import (
    Chinned,
    Discarded,
    Event,
    GameEnded,
    ReserveTaken,
    TurnAdvanced,
)
from canastra.web.codes import generate_room_code
from canastra.web.messages import EventMsg, ServerEnvelope
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

    def submit(self, action: Action) -> list[Event]:
        """Synchronous read-modify-write. NO ``await`` between read and write of self.state.

        Caller is responsible for catching ActionRejected and translating to a Rejected message.
        """
        assert self.state is not None, "Room.submit called before state initialized"
        new_state, events = apply(self.state, action)
        self.state = new_state
        if any(self._event_changes_deadline(ev) for ev in events):
            self.deadline_changed.set()
        return events

    @staticmethod
    def _event_changes_deadline(ev: Event) -> bool:
        """Heuristic: any TurnAdvanced or new turn-phase boundary may change the deadline.

        Conservative: returning True more often than necessary just wakes the timer loop,
        which is harmless.
        """
        return isinstance(ev, (TurnAdvanced, Discarded, ReserveTaken, Chinned, GameEnded))

    async def fanout(
        self,
        events: list[Event],
        *,
        action_seq: int,
        _send_timeout: float = 2.0,
    ) -> None:
        """Broadcast ``events`` to all seats that should receive each event.

        All events from a single ``submit()`` call share the same ``action_seq``
        because the engine bumps ``state.action_seq`` by 1 per action regardless
        of how many events that action emits. Callers should pass the
        post-submit ``self.state.action_seq``.

        ``ev.audience is None`` means all seats; otherwise only the matching seat.
        Sends are concurrent via ``asyncio.gather``; a slow or dead client is
        dropped via ``_mark_dead`` without blocking others.
        """
        seats_snapshot = list(self.seats.items())
        coros = []
        for ev in events:
            for seat, binding in seats_snapshot:
                if ev.audience is not None and ev.audience != seat:
                    continue
                if binding.ws is None:
                    continue
                envelope = ServerEnvelope(v=1, msg=EventMsg(event=ev, action_seq=action_seq))
                coros.append(self._send(binding, envelope, timeout=_send_timeout))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def _send(
        self,
        binding: SessionBinding,
        envelope: ServerEnvelope,
        *,
        timeout: float = 2.0,
    ) -> None:
        """Send ``envelope`` to ``binding.ws`` with a timeout.

        On any exception (including ``TimeoutError``), mark the binding dead.
        """
        ws = binding.ws
        if ws is None:
            return
        try:
            await asyncio.wait_for(ws.send_text(envelope.model_dump_json()), timeout)
        except Exception:
            await self._mark_dead(binding)

    async def _mark_dead(self, binding: SessionBinding) -> None:
        """Mark a session binding as dead and attempt a clean WebSocket close.

        Sets ``binding.ws = None`` first so subsequent fanout iterations skip it,
        then attempts ``ws.close(1011)`` best-effort (exceptions swallowed).
        """
        ws = binding.ws
        binding.ws = None
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close(code=1011)


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
