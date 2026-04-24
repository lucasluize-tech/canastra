"""CLI output formatting.

Every function is pure: it takes values, returns a string. No I/O, no
state, no side effects. The loop decides when to print.

Color codes come from `colored`, matching the legacy main.py palette:
    team 0:   yellow
    team 1:   blue
    errors:   white-on-dark-red
    prompts:  dark-bg bold  (handled in prompts.py/loop.py, not here)
"""

from __future__ import annotations

from colored import Back, Fore, Style

from canastra.domain.cards import Card

_ERROR_ON = f"{Fore.white}{Back.dark_red_1}"
_RESET = f"{Style.reset}"


def format_error(message: str) -> str:
    """Red-on-dark-red error line for BadInput or ActionRejected."""
    return f"{_ERROR_ON}  {message}{_RESET}"


def format_hand(hand: list[Card]) -> str:
    """Numbered 1-based card list for the active player's hand."""
    if not hand:
        return "(hand is empty)"
    lines = [f"  {i + 1:>2}. {card}" for i, card in enumerate(hand)]
    return "\n".join(lines)
