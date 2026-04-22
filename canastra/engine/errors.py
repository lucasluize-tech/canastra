"""Engine error types.

ActionRejected is the single public signal that an action is invalid
for the current state. Handlers MUST raise this (not return an error
event) so callers can decide retry / report / surface policy.
"""

from __future__ import annotations


class ActionRejected(Exception):
    """Raised when an action cannot be applied to the given state."""
