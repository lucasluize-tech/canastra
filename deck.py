"""Re-export shim — the real implementations live in ``canastra.domain.cards``.

Kept so existing callers (``player.py``, ``table.py``, ``main.py``, the
legacy test fixtures) keep working unchanged during the Phase-by-Phase
refactor. Delete once every caller imports from ``canastra.domain`` directly
(Phase 3).
"""

from canastra.domain.cards import (
    CLUBS as clubs,
)
from canastra.domain.cards import (
    DIAMONDS as diamonds,
)
from canastra.domain.cards import (
    HEARTS as hearts,
)
from canastra.domain.cards import (
    SPADES as spades,
)
from canastra.domain.cards import (
    Card,
    Deck,
)

__all__ = ["Card", "Deck", "clubs", "diamonds", "hearts", "spades"]
