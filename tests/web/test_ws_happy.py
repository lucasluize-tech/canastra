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
