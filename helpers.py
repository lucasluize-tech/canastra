"""Re-export shim — the real implementations live in ``canastra.domain``.

Kept so existing callers (``player.py``, ``table.py``, ``main.py``, the
legacy test fixtures) keep working unchanged during the Phase-by-Phase
refactor. Delete once every caller imports from ``canastra.domain`` directly
(Phase 3).
"""

from canastra.domain.rules import (
    WILD_RANK,
    extends_set,
    is_clean,
    is_in_order,
    rank_to_number,
)
from canastra.domain.scoring import points_for_set, points_from_set

__all__ = [
    "WILD_RANK",
    "extends_set",
    "is_clean",
    "is_in_order",
    "points_for_set",
    "points_from_set",
    "rank_to_number",
]
