"""Engine event types (discriminated union).

Events are the output side of apply(). They are broadcast to clients
(public) or routed to a single player (private; e.g. CardDrawn reveals
the card only to the drawer). Events are append-only per game and are
the basis of replay.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from canastra.domain.cards import Card
from canastra.engine.state import _card_from_dict, _card_to_dict


class _EventBase(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)


def _one(v: Any) -> Card:
    return _card_from_dict(v)


def _many(v: Any) -> list[Card]:
    return [_card_from_dict(x) for x in v]


class CardDrawn(_EventBase):
    type: Literal["card_drawn"] = "card_drawn"
    player_id: int
    card: Card

    @field_validator("card", mode="before")
    @classmethod
    def _v(cls, v: Any) -> Card:
        return _one(v)

    @field_serializer("card")
    def _s(self, c: Card) -> dict[str, Any]:
        return _card_to_dict(c)


class TrashPickedUp(_EventBase):
    type: Literal["trash_picked_up"] = "trash_picked_up"
    player_id: int
    cards: list[Card]

    @field_validator("cards", mode="before")
    @classmethod
    def _v(cls, v: Any) -> list[Card]:
        return _many(v)

    @field_serializer("cards")
    def _s(self, cs: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cs]


class MeldCreated(_EventBase):
    type: Literal["meld_created"] = "meld_created"
    player_id: int
    team_id: int
    meld_id: UUID
    cards: list[Card]

    @field_validator("cards", mode="before")
    @classmethod
    def _v(cls, v: Any) -> list[Card]:
        return _many(v)

    @field_serializer("cards")
    def _s(self, cs: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cs]


class MeldExtended(_EventBase):
    type: Literal["meld_extended"] = "meld_extended"
    player_id: int
    team_id: int
    meld_id: UUID
    added: list[Card]

    @field_validator("added", mode="before")
    @classmethod
    def _v(cls, v: Any) -> list[Card]:
        return _many(v)

    @field_serializer("added")
    def _s(self, cs: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cs]


class Discarded(_EventBase):
    type: Literal["discarded"] = "discarded"
    player_id: int
    card: Card

    @field_validator("card", mode="before")
    @classmethod
    def _v(cls, v: Any) -> Card:
        return _one(v)

    @field_serializer("card")
    def _s(self, c: Card) -> dict[str, Any]:
        return _card_to_dict(c)


class ReserveTaken(_EventBase):
    type: Literal["reserve_taken"] = "reserve_taken"
    player_id: int
    team_id: int
    reserves_remaining: int


class DeckReplenished(_EventBase):
    type: Literal["deck_replenished"] = "deck_replenished"
    team_id: int
    cards_added: int


class TurnAdvanced(_EventBase):
    type: Literal["turn_advanced"] = "turn_advanced"
    next_player_id: int


class Chinned(_EventBase):
    type: Literal["chinned"] = "chinned"
    team_id: int


class GameEnded(_EventBase):
    type: Literal["game_ended"] = "game_ended"
    winning_team: int | None
    scores: dict[int, int]

    @field_validator("scores", mode="before")
    @classmethod
    def _v(cls, v: Any) -> dict[int, int]:
        return {int(k): int(vv) for k, vv in v.items()}


Event = Annotated[
    CardDrawn
    | TrashPickedUp
    | MeldCreated
    | MeldExtended
    | Discarded
    | ReserveTaken
    | DeckReplenished
    | TurnAdvanced
    | Chinned
    | GameEnded,
    Field(discriminator="type"),
]
