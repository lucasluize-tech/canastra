"""Compile-time guard: Room.submit is synchronous end-to-end.

The fanout side is async, but the read-modify-write of engine state must stay
inside one event-loop tick — otherwise concurrent SubmitAction handlers could
interleave on the same room and corrupt action_seq."""

import inspect

from canastra.web.rooms import Room


def test_room_submit_is_synchronous():
    assert not inspect.iscoroutinefunction(Room.submit)


def test_room_submit_source_has_no_await():
    src = inspect.getsource(Room.submit)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert " await " not in stripped, f"Room.submit must not await: {line!r}"
        assert not stripped.startswith("await "), f"Room.submit must not await: {line!r}"
