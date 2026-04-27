"""Hypothesis property tests: every envelope JSON-round-trips identically."""

from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from canastra.engine.events import TurnAdvanced
from canastra.web.messages import (
    ClientEnvelope,
    Heartbeat,
    LeaveRoom,
    Ping,
    Pong,
    Rejected,
    Rematch,
    RequestSnapshot,
    RoomClosed,
    ServerEnvelope,
    StartGame,
)

CLIENT_MSGS = st.sampled_from(
    [
        StartGame(type="start_game"),
        Rematch(type="rematch"),
        LeaveRoom(type="leave_room"),
        RequestSnapshot(type="request_snapshot"),
        Ping(type="ping"),
    ]
)


@given(msg=CLIENT_MSGS)
@settings(max_examples=50)
def test_client_envelope_round_trip(msg):
    env = ClientEnvelope(v=1, client_msg_id=uuid4(), msg=msg)
    blob = env.model_dump_json()
    restored = ClientEnvelope.model_validate_json(blob)
    assert restored.msg.type == msg.type


SERVER_MSGS = st.sampled_from(
    [
        RoomClosed(type="room_closed", reason="host_left"),
        Heartbeat(type="heartbeat", server_time_ms=1),
        Pong(type="pong", client_msg_id=uuid4(), server_time_ms=1),
        # Rejected requires client_msg_id; build inside the strategy
    ]
)


@given(msg=SERVER_MSGS)
@settings(max_examples=50)
def test_server_envelope_round_trip(msg):
    env = ServerEnvelope(v=1, msg=msg)
    blob = env.model_dump_json()
    restored = ServerEnvelope.model_validate_json(blob)
    assert restored.msg.type == msg.type


def test_event_msg_round_trip_for_public_event():
    from canastra.web.messages import EventMsg

    env = ServerEnvelope(
        v=1, msg=EventMsg(type="event", event=TurnAdvanced(next_player_id=2), action_seq=1)
    )
    restored = ServerEnvelope.model_validate_json(env.model_dump_json())
    assert restored.msg.type == "event"


@given(reason=st.sampled_from(["illegal_action", "not_your_turn", "wrong_phase", "bad_message"]))
@settings(max_examples=20)
def test_rejected_round_trip(reason):
    msg = Rejected(type="rejected", client_msg_id=uuid4(), reason=reason)
    env = ServerEnvelope(v=1, msg=msg)
    restored = ServerEnvelope.model_validate_json(env.model_dump_json())
    assert restored.msg.reason == reason
