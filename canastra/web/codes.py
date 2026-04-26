"""Crockford Base32 room-code generator.

The alphabet excludes I, L, O, U to reduce dictation errors. Six characters give
~10^9 entropy — far more than needed at family scale (<50 live rooms).
"""

import random

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_room_code(rng: random.SystemRandom) -> str:
    """Return a fresh 6-char room code drawn uniformly from `ALPHABET`."""
    return "".join(rng.choice(ALPHABET) for _ in range(6))
