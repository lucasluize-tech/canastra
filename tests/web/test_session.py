"""Tests for session binding, store, and cookie sign/verify."""

import time

from canastra.web.session import (
    SessionStore,
    new_session_id,
    sign_cookie,
    verify_cookie,
)

SECRET = b"a" * 32


def test_new_session_id_is_url_safe_and_long():
    sid = new_session_id()
    assert isinstance(sid, str)
    assert len(sid) >= 32


def test_sign_then_verify_round_trip():
    sid = new_session_id()
    blob = sign_cookie(sid, SECRET)
    assert verify_cookie(blob, SECRET, max_age=3600) == sid


def test_verify_rejects_tampered_cookie():
    sid = new_session_id()
    blob = sign_cookie(sid, SECRET)
    # Replace the entire signature segment with a bogus one. Single-char
    # tampering of base64 is unreliable: when the changed byte falls on
    # an unused-bit boundary of the base64 group, the decoded HMAC bytes
    # are unchanged and the cookie still verifies.
    tampered = blob.rsplit(".", 1)[0] + ".AAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert verify_cookie(tampered, SECRET, max_age=3600) is None


def test_verify_rejects_wrong_secret():
    sid = new_session_id()
    blob = sign_cookie(sid, SECRET)
    other = b"b" * 32
    assert verify_cookie(blob, other, max_age=3600) is None


def test_verify_rejects_expired_cookie():
    """A cookie older than max_age must verify to None."""
    sid = new_session_id()
    blob = sign_cookie(sid, SECRET)
    # max_age=0 forces immediate expiry on the next call
    time.sleep(1)
    assert verify_cookie(blob, SECRET, max_age=0) is None


def test_session_store_new_get_revoke():
    store = SessionStore()
    binding = store.new(room_code="ABC123", seat=0, nickname="Alice")
    assert binding.room_code == "ABC123"
    assert binding.seat == 0
    assert binding.nickname == "Alice"

    assert store.get(binding.session_id) is binding
    store.revoke(binding.session_id)
    assert store.get(binding.session_id) is None


def test_session_binding_has_ws_lock_and_recent_results():
    import asyncio
    from collections import OrderedDict

    store = SessionStore()
    b = store.new(room_code="ABC123", seat=0, nickname="Alice")
    assert isinstance(b.ws_lock, asyncio.Lock)
    assert isinstance(b.recent_results, OrderedDict)
    assert b.ws is None


def test_session_binding_remember_result_is_bounded_to_64():
    """remember_result evicts oldest entries beyond capacity."""
    from uuid import uuid4

    store = SessionStore()
    b = store.new(room_code="ABC123", seat=0, nickname="Alice")
    for _ in range(100):
        b.remember_result(uuid4(), [])
    assert len(b.recent_results) == 64


def test_session_store_all_for_room():
    store = SessionStore()
    a = store.new(room_code="ROOM1", seat=0, nickname="Alice")
    b = store.new(room_code="ROOM1", seat=1, nickname="Bob")
    c = store.new(room_code="ROOM2", seat=0, nickname="Carol")
    members = store.all_for_room("ROOM1")
    assert {x.session_id for x in members} == {a.session_id, b.session_id}
    assert c.session_id not in {x.session_id for x in members}
