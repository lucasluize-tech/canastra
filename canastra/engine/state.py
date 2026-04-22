"""Engine state models (pydantic v2).

These are serializable value objects. No behavior lives here — logic is
in canastra/engine/engine.py and canastra/engine/scoring.py. All models
are frozen so handlers must explicitly rebuild state when they change
it (no accidental in-place mutation).
"""

from __future__ import annotations

from enum import Enum
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


PlayerId = int
TeamId = int


class Phase(str, Enum):
    WAITING_DRAW = "waiting_draw"
    PLAYING = "playing"
    DISCARDING = "discarding"
    ENDED = "ended"


class TurnState(BaseModel):
    model_config = ConfigDict(frozen=True)

    player_id: PlayerId
    phase: Phase
    deadline_at: float | None = None  # unix epoch seconds; None = no timer


def _cards_before(v: Any) -> list[Card]:
    return [_card_from_dict(x) for x in v]


def _cards_after(cards: list[Card]) -> list[dict[str, Any]]:
    return [_card_to_dict(c) for c in cards]


class GameState(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: GameConfig
    seat_order: list[PlayerId]
    teams: dict[TeamId, list[PlayerId]]
    hands: dict[PlayerId, list[Card]]
    melds: dict[TeamId, list[Meld]]
    reserves: dict[TeamId, list[list[Card]]]  # stack of reserve hands per team
    reserves_used: dict[TeamId, int]
    deck: list[Card]
    trash: list[Card]
    current_turn: TurnState
    phase: Phase
    action_seq: int = 0
    winning_team: TeamId | None = None
    chin_team: TeamId | None = None

    @field_validator("hands", "deck", "trash", mode="before")
    @classmethod
    def _parse_card_lists(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return {int(k): _cards_before(vv) for k, vv in v.items()}
        return _cards_before(v)

    @field_validator("reserves", mode="before")
    @classmethod
    def _parse_reserves(cls, v: Any) -> Any:
        return {int(k): [_cards_before(h) for h in stacks] for k, stacks in v.items()}

    @field_validator("teams", "reserves_used", mode="before")
    @classmethod
    def _parse_int_keys(cls, v: Any) -> Any:
        return {int(k): vv for k, vv in v.items()}

    @field_serializer("hands")
    def _ser_hands(self, hands: dict[PlayerId, list[Card]]) -> dict[str, list[dict[str, Any]]]:
        return {str(k): _cards_after(v) for k, v in hands.items()}

    @field_serializer("deck", "trash")
    def _ser_card_list(self, cards: list[Card]) -> list[dict[str, Any]]:
        return _cards_after(cards)

    @field_serializer("reserves")
    def _ser_reserves(
        self, reserves: dict[TeamId, list[list[Card]]]
    ) -> dict[str, list[list[dict[str, Any]]]]:
        return {str(k): [_cards_after(h) for h in stacks] for k, stacks in reserves.items()}
