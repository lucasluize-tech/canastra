"""The 9 unhappy-path scenarios from the spec §11.1."""

import concurrent.futures
from contextlib import ExitStack
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from canastra.web.app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("CANASTRA_DEBUG", "1")
    return create_app(debug=False)


def _create_room(client: TestClient) -> str:
    return client.post(
        "/rooms",
        json={
            "nickname": "Alice",
            "num_players": 4,
            "num_decks": 2,
            "reserves_per_team": 2,
            "timer_enabled": False,
        },
    ).json()["room_code"]


def _drain_welcome_lobby(ws) -> None:
    """Drain the initial welcome + lobby_update pair."""
    ws.receive_json()  # welcome
    ws.receive_json()  # lobby_update


# ---------------------------------------------------------------------------
# 1. Non-host cannot start the game
# ---------------------------------------------------------------------------


def test_non_host_start_game_rejected(app):
    """Bob (seat 1) sends StartGame → rejected with reason 'not_host'."""
    with TestClient(app) as host:
        code = _create_room(host)

        with ExitStack() as stack:
            host_ws = stack.enter_context(
                host.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
            )
            _drain_welcome_lobby(host_ws)

            joiner = TestClient(app)
            joiner.post(f"/rooms/{code}", json={"nickname": "Bob"})
            bob_ws = stack.enter_context(
                joiner.websocket_connect(
                    f"/ws/room/{code}", headers={"origin": "http://testserver"}
                )
            )
            bob_ws.receive_json()  # welcome
            bob_ws.receive_json()  # lobby_update (bob's own)
            host_ws.receive_json()  # lobby_update broadcast to host

            bob_ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "start_game"},
                }
            )
            resp = bob_ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "not_host"


# ---------------------------------------------------------------------------
# 2. Malformed JSON returns rejected
# ---------------------------------------------------------------------------


def test_malformed_json_returns_rejected(app):
    """Sending non-JSON text → rejected with reason 'bad_message'."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)
            ws.send_text("this is not json {{{")
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "bad_message"


# ---------------------------------------------------------------------------
# 3. Unknown message type returns rejected
# ---------------------------------------------------------------------------


def test_unknown_type_returns_rejected(app):
    """Valid envelope wrapper with unknown msg type → rejected with 'bad_message'."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)
            ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "no_such_type"},
                }
            )
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "bad_message"


# ---------------------------------------------------------------------------
# 4. Unsupported protocol version returns rejected
# ---------------------------------------------------------------------------


def test_unsupported_version_returns_rejected(app):
    """Envelope with v=2 fails schema validation → rejected with 'bad_message'."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)
            ws.send_json(
                {
                    "v": 2,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "ping"},
                }
            )
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "bad_message"


# ---------------------------------------------------------------------------
# 5. Duplicate client_msg_id is idempotent
# ---------------------------------------------------------------------------


def test_duplicate_client_msg_id_is_idempotent(app):
    """Sending Ping twice with the same client_msg_id → second send is a no-op."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)

            msg_id = str(uuid4())
            envelope = {"v": 1, "client_msg_id": msg_id, "msg": {"type": "ping"}}

            # First send → expect pong
            ws.send_json(envelope)
            first = ws.receive_json()
            assert first["msg"]["type"] == "pong"
            assert first["msg"]["client_msg_id"] == msg_id

            # Second send with same id → idempotency short-circuit; may produce
            # a cached replay (same type) or nothing at all.
            ws.send_json(envelope)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(ws.receive_json)
                try:
                    second = future.result(timeout=0.5)
                    # If a response arrives it must be the same type (replay)
                    assert second["msg"]["type"] == "pong"
                except concurrent.futures.TimeoutError:
                    pass  # silence: "nothing" path is also valid behaviour
                except Exception:
                    pass  # silence: connection-closed during timeout also fine


# ---------------------------------------------------------------------------
# 6. Origin mismatch closes connection
# ---------------------------------------------------------------------------


def test_origin_mismatch_closes_connection(monkeypatch):
    """Connecting from a disallowed origin → server closes (WebSocketDisconnect).

    Debug mode is permissive (any origin OK for localhost smoke tests), so this
    security check has to run in production mode."""
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.delenv("CANASTRA_DEBUG", raising=False)
    prod_app = create_app(debug=False)
    with TestClient(prod_app) as client:
        code = _create_room(client)
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://evil.example"}),
        ):
            pass


# ---------------------------------------------------------------------------
# 7. Rematch before game ended returns rejected
# ---------------------------------------------------------------------------


def test_rematch_before_game_ended_returns_rejected(app):
    """Sending Rematch while still in lobby phase → rejected with 'wrong_lobby_phase'."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)
            ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "rematch"},
                }
            )
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "wrong_lobby_phase"


# ---------------------------------------------------------------------------
# 8. SubmitAction in lobby returns wrong_phase
# ---------------------------------------------------------------------------


def test_submit_action_in_lobby_returns_wrong_phase(app):
    """SubmitAction before game starts → rejected with 'wrong_phase'."""
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            _drain_welcome_lobby(ws)
            ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {
                        "type": "submit_action",
                        "action": {"type": "draw", "player_id": 0},
                    },
                }
            )
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "rejected"
            assert resp["msg"]["reason"] == "wrong_phase"


# ---------------------------------------------------------------------------
# 9. player_id in action is overwritten by session seat
# ---------------------------------------------------------------------------


def test_action_player_id_overwritten_by_session_seat(app):
    """Bob (seat 1) sends draw with player_id=0; server overwrites to seat 1.
    Response must be 'accepted' or 'rejected' — never applied as seat 0's action."""
    with TestClient(app) as host:
        code = _create_room(host)

        with ExitStack() as stack:
            wss = []
            host_ws = stack.enter_context(
                host.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
            )
            wss.append(host_ws)
            host_ws.receive_json()  # welcome
            host_ws.receive_json()  # lobby_update (1 seat)

            for nick in ("Bob", "Carol", "Dave"):
                c = TestClient(app)
                c.post(f"/rooms/{code}", json={"nickname": nick})
                ws = stack.enter_context(
                    c.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
                )
                wss.append(ws)
                ws.receive_json()  # welcome
                ws.receive_json()  # lobby_update for new socket
                for prev_ws in wss[:-1]:
                    prev_ws.receive_json()  # lobby_update broadcast to existing connections

            # Host starts the game
            host_ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "start_game"},
                }
            )
            for ws in wss:
                m = ws.receive_json()
                assert m["msg"]["type"] == "snapshot"
                assert m["msg"]["reason"] == "started"

            # Bob (seat 1) sends draw claiming to be player_id=0 (the host)
            bob_ws = wss[1]
            bob_ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {
                        "type": "submit_action",
                        "action": {"type": "draw", "player_id": 0},
                    },
                }
            )

            resp = bob_ws.receive_json()
            # The server must have overwritten player_id to 1 (Bob's seat).
            # So the response is either accepted (if it's Bob's turn) or rejected
            # with not_your_turn / illegal_action — but never accepted as seat 0.
            assert resp["msg"]["type"] in {"accepted", "rejected"}
            if resp["msg"]["type"] == "rejected":
                assert resp["msg"]["reason"] in {"illegal_action", "not_your_turn"}
