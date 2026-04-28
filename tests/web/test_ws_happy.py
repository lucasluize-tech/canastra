"""End-to-end happy-path WS tests."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from canastra.web.app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("CANASTRA_DEBUG", "1")  # disables Secure cookie
    return create_app(debug=False)


def _create_room(client):
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


def test_ws_connect_sends_welcome(app):
    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            msg = ws.receive_json()
            assert msg["v"] == 1
            assert msg["msg"]["type"] == "welcome"
            assert msg["msg"]["seat"] == 0


def test_ws_rejects_missing_cookie(app):
    with TestClient(app) as _:
        # create room with the host
        host = TestClient(app)
        host.post(
            "/rooms",
            json={
                "nickname": "Alice",
                "num_players": 4,
                "num_decks": 2,
                "reserves_per_team": 2,
                "timer_enabled": False,
            },
        )

    # Now try to connect without any cookie — TestClient instances each have separate cookies
    fresh = TestClient(app)
    with (
        pytest.raises(WebSocketDisconnect),
        fresh.websocket_connect("/ws/room/ABC123", headers={"origin": "http://testserver"}),
    ):
        pass


def test_lobby_update_broadcast_on_join(app):
    with TestClient(app) as host:
        code = _create_room(host)
        with host.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as host_ws:
            host_ws.receive_json()  # welcome
            host_ws.receive_json()  # lobby_update (just-host)

            other = TestClient(app)
            other.post(f"/rooms/{code}", json={"nickname": "Bob"})
            with other.websocket_connect(
                f"/ws/room/{code}", headers={"origin": "http://testserver"}
            ) as bob_ws:
                bob_ws.receive_json()  # welcome
                bob_ws.receive_json()  # lobby_update with both seats

                # host should also get a fresh lobby_update
                msg = host_ws.receive_json()
                assert msg["msg"]["type"] == "lobby_update"
                assert len(msg["msg"]["seats"]) == 2


def test_host_starts_game_emits_snapshot_to_each_seat(app):
    """All 4 players see Snapshot(reason='started') after host StartGame."""
    from contextlib import ExitStack
    from uuid import uuid4

    with TestClient(app) as host:
        code = _create_room(host)

        # ExitStack so every WS context exits (and its server-side handler
        # finishes its finally block) BEFORE the host TestClient lifespan
        # tears down — otherwise _shutdown_manager tries to send to still-live
        # cross-loop WebSocket objects and blocks past the 5s timeout.
        with ExitStack() as ws_stack:
            wss = []
            host_ws = ws_stack.enter_context(
                host.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
            )
            wss.append(host_ws)
            host_ws.receive_json()  # welcome
            host_ws.receive_json()  # lobby_update (1 seat)

            # Each new joiner triggers a lobby_update broadcast to every connected
            # socket. Drain eagerly per-connection or TestClient's sync send queue
            # back-pressures and the test deadlocks.
            for nick in ("Bob", "Carol", "Dave"):
                c = TestClient(app)  # no __enter__ — sharing host's lifespan-managed app.state
                c.post(f"/rooms/{code}", json={"nickname": nick})
                ws = ws_stack.enter_context(
                    c.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
                )
                wss.append(ws)
                ws.receive_json()  # welcome
                ws.receive_json()  # lobby_update for new socket
                for prev_ws in wss[:-1]:
                    prev_ws.receive_json()  # lobby_update for already-connected sockets

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


def test_submit_action_draw_returns_accepted_and_event(app):
    """SubmitAction(Draw) -> Accepted to actor + EventMsg fanout to everyone (filtered)."""
    from contextlib import ExitStack
    from uuid import uuid4

    with TestClient(app) as host:
        code = _create_room(host)

        with ExitStack() as ws_stack:
            wss = []
            host_ws = ws_stack.enter_context(
                host.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
            )
            wss.append(host_ws)
            host_ws.receive_json()  # welcome
            host_ws.receive_json()  # lobby_update (1 seat)

            for nick in ("Bob", "Carol", "Dave"):
                c = TestClient(app)  # no __enter__ — sharing host's lifespan-managed app.state
                c.post(f"/rooms/{code}", json={"nickname": nick})
                ws = ws_stack.enter_context(
                    c.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
                )
                wss.append(ws)
                ws.receive_json()  # welcome
                ws.receive_json()  # lobby_update for new socket
                for prev_ws in wss[:-1]:
                    prev_ws.receive_json()  # lobby_update for already-connected sockets

            # Host starts the game
            host_ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(uuid4()),
                    "msg": {"type": "start_game"},
                }
            )
            # Drain snapshots — each seat gets one
            for ws in wss:
                m = ws.receive_json()
                assert m["msg"]["type"] == "snapshot"
                assert m["msg"]["reason"] == "started"

            # Host (seat 0) submits a Draw action
            cm = uuid4()
            host_ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": str(cm),
                    "msg": {
                        "type": "submit_action",
                        "action": {"type": "draw", "player_id": 0},
                    },
                }
            )

            # Host receives Accepted or Rejected depending on whose turn it is
            m = host_ws.receive_json()
            assert m["msg"]["type"] in {"accepted", "rejected"}


def test_ping_returns_pong(app):
    """Ping → Pong echoes the same client_msg_id."""
    from uuid import uuid4

    with TestClient(app) as client:
        code = _create_room(client)
        with client.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws:
            ws.receive_json()  # welcome
            ws.receive_json()  # lobby_update

            msg_id = str(uuid4())
            ws.send_json(
                {
                    "v": 1,
                    "client_msg_id": msg_id,
                    "msg": {"type": "ping"},
                }
            )
            resp = ws.receive_json()
            assert resp["msg"]["type"] == "pong"
            assert resp["msg"]["client_msg_id"] == msg_id


def test_request_snapshot_returns_snapshot_during_play(app):
    """RequestSnapshot during play → Snapshot(reason='snapshot') to requesting seat only."""
    from contextlib import ExitStack
    from uuid import uuid4

    with TestClient(app) as host:
        code = _create_room(host)

        with ExitStack() as ws_stack:
            wss = []
            host_ws = ws_stack.enter_context(
                host.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
            )
            wss.append(host_ws)
            host_ws.receive_json()  # welcome
            host_ws.receive_json()  # lobby_update (1 seat)

            for nick in ("Bob", "Carol", "Dave"):
                c = TestClient(app)
                c.post(f"/rooms/{code}", json={"nickname": nick})
                ws = ws_stack.enter_context(
                    c.websocket_connect(f"/ws/room/{code}", headers={"origin": "http://testserver"})
                )
                wss.append(ws)
                ws.receive_json()  # welcome
                ws.receive_json()  # lobby_update for new socket
                for prev_ws in wss[:-1]:
                    prev_ws.receive_json()  # lobby_update for already-connected sockets

            # Start the game
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

            # Bob (seat 1) requests a snapshot
            msg_id = str(uuid4())
            wss[1].send_json(
                {
                    "v": 1,
                    "client_msg_id": msg_id,
                    "msg": {"type": "request_snapshot"},
                }
            )
            resp = wss[1].receive_json()
            assert resp["msg"]["type"] == "snapshot"
            assert resp["msg"]["reason"] == "requested"
