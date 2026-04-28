"""Lifespan + create_app guards."""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from canastra.web.app import create_app


def test_create_app_returns_fastapi_in_debug():
    app = create_app(debug=True)
    assert isinstance(app, FastAPI)


def test_create_app_requires_secret_in_non_debug(monkeypatch):
    monkeypatch.delenv("CANASTRA_SESSION_SECRET", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    with pytest.raises(AssertionError, match="CANASTRA_SESSION_SECRET"):
        create_app(debug=False)


def test_create_app_requires_workers_one_in_non_debug(monkeypatch):
    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    with pytest.raises(AssertionError, match="workers 1"):
        create_app(debug=False)


def test_create_app_attaches_room_manager_in_lifespan(monkeypatch):
    """RoomManager and bytes secret are attached to app.state during lifespan startup."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CANASTRA_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    app = create_app(debug=False)
    with TestClient(app):
        assert getattr(app.state, "manager", None) is not None
        assert isinstance(app.state.secret, bytes)
