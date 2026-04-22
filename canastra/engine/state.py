"""Engine state models (pydantic v2).

These are serializable value objects. No behavior lives here — logic is
in canastra/engine/engine.py and canastra/engine/scoring.py. All models
are frozen so handlers must explicitly rebuild state when they change
it (no accidental in-place mutation).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from canastra.domain.cards import Card


class GameConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    num_players: int = Field(ge=4)
    num_decks: int = Field(ge=2)
    reserves_per_team: int = Field(ge=2)
    timer_enabled: bool = False
    seed: int

    @property
    def num_teams(self) -> int:
        return 2

    @property
    def players_per_team(self) -> int:
        return self.num_players // 2

    @model_validator(mode="after")
    def _validate_combo(self) -> GameConfig:
        if self.num_players % 2 != 0:
            raise ValueError("num_players must be even (two equal teams)")
        if self.num_decks % 2 != 0:
            raise ValueError("num_decks must be even")
        if self.reserves_per_team > self.num_decks:
            raise ValueError("reserves_per_team must be <= num_decks")
        return self


def _card_to_dict(c: Card) -> dict[str, Any]:
    return {"suit": c.suit, "rank": c.rank}


def _card_from_dict(d: Any) -> Card:
    if isinstance(d, Card):
        return d
    return Card(d["suit"], d["rank"])


class Meld(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    cards: list[Card]
    permanent_dirty: bool = False

    @field_validator("cards", mode="before")
    @classmethod
    def _parse_cards(cls, v: Any) -> list[Card]:
        return [_card_from_dict(x) for x in v]

    @field_serializer("cards")
    def _serialize_cards(self, cards: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cards]
