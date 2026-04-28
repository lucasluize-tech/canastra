"""Reconnect flow: cookie survives WS close; new connection gets a Snapshot(reconnect)."""

from contextlib import ExitStack
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from canastra.web.app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("CANASTRA_DEBUG", "1")
    return create_app(debug=False)


def test_reconnect_in_lobby_receives_lobby_update(app):
    with TestClient(app) as host:
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
        code = next(iter(host.app.state.manager.rooms))

        with host.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws1:
            ws1.receive_json()  # welcome
            ws1.receive_json()  # lobby_update

        with host.websocket_connect(
            f"/ws/room/{code}", headers={"origin": "http://testserver"}
        ) as ws2:
            m = ws2.receive_json()
            assert m["msg"]["type"] == "welcome"
            m = ws2.receive_json()
            assert m["msg"]["type"] == "lobby_update"


def test_reconnect_during_play_receives_snapshot_reconnect(app):
    with TestClient(app) as host:
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
        code = next(iter(host.app.state.manager.rooms))

        with ExitStack() as ws_stack:
            others = []
            for nick in ("Bob", "Carol", "Dave"):
                c = TestClient(app)
                c.post(f"/rooms/{code}", json={"nickname": nick})
                others.append(
                    ws_stack.enter_context(
                        c.websocket_connect(
                            f"/ws/room/{code}",
                            headers={"origin": "http://testserver"},
                        )
                    )
                )

            with host.websocket_connect(
                f"/ws/room/{code}", headers={"origin": "http://testserver"}
            ) as ws1:
                all_wss = [ws1, *others]
                for ws in all_wss:
                    while True:
                        m = ws.receive_json()
                        if m["msg"]["type"] == "lobby_update" and len(m["msg"]["seats"]) == 4:
                            break

                ws1.send_json(
                    {
                        "v": 1,
                        "client_msg_id": str(uuid4()),
                        "msg": {"type": "start_game"},
                    }
                )
                for ws in all_wss:
                    ws.receive_json()  # snapshot started

            with host.websocket_connect(
                f"/ws/room/{code}", headers={"origin": "http://testserver"}
            ) as ws1b:
                m = ws1b.receive_json()
                assert m["msg"]["type"] == "welcome"
                m = ws1b.receive_json()
                assert m["msg"]["type"] == "snapshot"
                assert m["msg"]["reason"] == "reconnect"
