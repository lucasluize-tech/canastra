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
