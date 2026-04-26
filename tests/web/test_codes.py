"""Tests for Crockford-Base32 room-code generator."""

import random
import re

from canastra.web.codes import ALPHABET, generate_room_code


def test_alphabet_is_crockford_base32():
    assert len(ALPHABET) == 32
    for forbidden in ("I", "L", "O", "U"):
        assert forbidden not in ALPHABET
    assert "0" in ALPHABET
    assert "1" in ALPHABET


def test_generate_room_code_is_six_chars():
    rng = random.SystemRandom()
    code = generate_room_code(rng)
    assert len(code) == 6


def test_generate_room_code_only_uses_alphabet():
    rng = random.SystemRandom()
    pattern = re.compile(f"^[{re.escape(ALPHABET)}]+$")
    for _ in range(100):
        assert pattern.match(generate_room_code(rng))


def test_codes_are_not_identical_across_calls():
    """SystemRandom should not produce duplicates over a small sample."""
    rng = random.SystemRandom()
    codes = {generate_room_code(rng) for _ in range(100)}
    assert len(codes) >= 95  # extremely loose; collision probability is ~0
