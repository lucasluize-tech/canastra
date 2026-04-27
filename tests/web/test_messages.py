"""Tests for WS envelope + discriminated unions."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from canastra.domain.cards import HEARTS, Card
from canastra.engine.actions import Discard
from canastra.web.messages import (
    ClientEnvelope,
    LeaveRoom,
    Ping,
    Rematch,
    RequestSnapshot,
    StartGame,
    SubmitAction,
)


def test_envelope_carries_v_and_msg_id():
    msg = ClientEnvelope(
        v=1,
        client_msg_id=uuid4(),
        msg=Ping(type="ping"),
    )
    assert msg.v == 1


def test_start_game_round_trip():
    env = ClientEnvelope(v=1, client_msg_id=uuid4(), msg=StartGame(type="start_game"))
    blob = env.model_dump_json()
    restored = ClientEnvelope.model_validate_json(blob)
    assert isinstance(restored.msg, StartGame)


def test_submit_action_round_trip():
    card = Card(suit=HEARTS, rank=5)
    action = Discard(player_id=0, card=card)
    env = ClientEnvelope(
        v=1, client_msg_id=uuid4(), msg=SubmitAction(type="submit_action", action=action)
    )
    blob = env.model_dump_json()
    restored = ClientEnvelope.model_validate_json(blob)
    assert isinstance(restored.msg, SubmitAction)
    assert isinstance(restored.msg.action, Discard)


def test_unknown_type_rejected():
    payload = {"v": 1, "client_msg_id": str(uuid4()), "msg": {"type": "no_such_type"}}
    with pytest.raises(ValidationError):
        ClientEnvelope.model_validate(payload)


def test_unknown_v_rejected():
    payload = {
        "v": 2,
        "client_msg_id": str(uuid4()),
        "msg": {"type": "ping"},
    }
    with pytest.raises(ValidationError):
        ClientEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "msg_cls,extra",
    [
        (Ping, {}),
        (StartGame, {}),
        (Rematch, {}),
        (LeaveRoom, {}),
        (RequestSnapshot, {}),
    ],
)
def test_no_arg_client_messages_round_trip(msg_cls, extra):
    type_str = msg_cls.model_fields["type"].default
    env = ClientEnvelope(
        v=1,
        client_msg_id=uuid4(),
        msg=msg_cls(type=type_str, **extra),
    )
    json.loads(env.model_dump_json())


# ---------- Server → Client ----------

from canastra.engine import GameConfig, initial_state  # noqa: E402
from canastra.engine.events import TurnAdvanced  # noqa: E402
from canastra.web.messages import (  # noqa: E402
    Accepted,
    DeadlineWarning,
    EventMsg,
    Heartbeat,
    LobbyUpdate,
    Pong,
    Rejected,
    RoomClosed,
    RoomPublic,
    SeatInfo,
    ServerEnvelope,
    Snapshot,
    Welcome,
)


def _public_room() -> RoomPublic:
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=1)
    return RoomPublic(
        code="ABC123",
        host_seat=0,
        config=cfg,
        phase="lobby",
        seats=[
            SeatInfo(seat=0, nickname="Alice", connected=True),
            SeatInfo(seat=1, nickname="Bob", connected=True),
        ],
    )


def test_welcome_round_trip():
    env = ServerEnvelope(v=1, msg=Welcome(type="welcome", seat=0, room=_public_room()))
    blob = env.model_dump_json()
    ServerEnvelope.model_validate_json(blob)


def test_lobby_update_full_list():
    env = ServerEnvelope(
        v=1,
        msg=LobbyUpdate(
            type="lobby_update",
            seats=[
                SeatInfo(seat=0, nickname="Alice", connected=True),
                SeatInfo(seat=1, nickname="Bob", connected=False),
            ],
        ),
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_snapshot_round_trip():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=1)
    state = initial_state(cfg)
    view = state.view_for(seat=0)
    env = ServerEnvelope(
        v=1,
        msg=Snapshot(
            type="snapshot",
            reason="started",
            snapshot=view,
            action_seq=state.action_seq,
            deadline_ms=None,
        ),
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_event_msg_round_trip():
    ev = TurnAdvanced(next_player_id=2)
    env = ServerEnvelope(v=1, msg=EventMsg(type="event", event=ev, action_seq=42))
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_accepted_carries_client_msg_id():
    cm = uuid4()
    env = ServerEnvelope(
        v=1, msg=Accepted(type="accepted", client_msg_id=cm, action_seq=99)
    )
    restored = ServerEnvelope.model_validate_json(env.model_dump_json())
    assert isinstance(restored.msg, Accepted)
    assert restored.msg.client_msg_id == cm


def test_rejected_reason_is_enum():
    cm = uuid4()
    env = ServerEnvelope(
        v=1,
        msg=Rejected(
            type="rejected",
            client_msg_id=cm,
            reason="illegal_action",
            detail="card not in hand",
        ),
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_room_closed_reason_is_enum():
    env = ServerEnvelope(v=1, msg=RoomClosed(type="room_closed", reason="host_left"))
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_deadline_warning_round_trip():
    env = ServerEnvelope(
        v=1, msg=DeadlineWarning(type="deadline_warning", deadline_ms=1700000000000)
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_heartbeat_round_trip():
    env = ServerEnvelope(
        v=1, msg=Heartbeat(type="heartbeat", server_time_ms=1700000000000)
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())


def test_pong_round_trip():
    cm = uuid4()
    env = ServerEnvelope(
        v=1, msg=Pong(type="pong", client_msg_id=cm, server_time_ms=1700000000000)
    )
    ServerEnvelope.model_validate_json(env.model_dump_json())
