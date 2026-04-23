"""Engine action types (discriminated union).

Actions are the input side of apply(state, action) -> (state', events).
They are the only way state changes. Every action carries the
player_id of the actor; the engine validates the actor matches the
current turn (or is a chin / timeout on their team).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from canastra.domain.cards import Card
from canastra.engine.state import _card_from_dict, _card_to_dict


class _ActionBase(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    player_id: int


def _one_card_validator(v: Any) -> Card:
    return _card_from_dict(v)


def _card_list_validator(v: Any) -> list[Card]:
    return [_card_from_dict(x) for x in v]


class Draw(_ActionBase):
    type: Literal["draw"] = "draw"


class PickUpTrash(_ActionBase):
    type: Literal["pickup_trash"] = "pickup_trash"


class CreateMeld(_ActionBase):
    type: Literal["create_meld"] = "create_meld"
    cards: list[Card]

    @field_validator("cards", mode="before")
    @classmethod
    def _v(cls, v: Any) -> list[Card]:
        return _card_list_validator(v)

    @field_serializer("cards")
    def _s(self, cards: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cards]


class ExtendMeld(_ActionBase):
    type: Literal["extend_meld"] = "extend_meld"
    meld_id: UUID
    cards: list[Card]

    @field_validator("cards", mode="before")
    @classmethod
    def _v(cls, v: Any) -> list[Card]:
        return _card_list_validator(v)

    @field_serializer("cards")
    def _s(self, cards: list[Card]) -> list[dict[str, Any]]:
        return [_card_to_dict(c) for c in cards]


class Discard(_ActionBase):
    type: Literal["discard"] = "discard"
    card: Card

    @field_validator("card", mode="before")
    @classmethod
    def _v(cls, v: Any) -> Card:
        return _one_card_validator(v)

    @field_serializer("card")
    def _s(self, card: Card) -> dict[str, Any]:
        return _card_to_dict(card)


class Chin(_ActionBase):
    """Voluntary 'I'm out' signal. In the canonical rules chin triggers
    automatically when a hand is emptied with no reserves left, but we
    keep an explicit action for replay logs and forfeits.
    """

    type: Literal["chin"] = "chin"


Action = Annotated[
    Draw | PickUpTrash | CreateMeld | ExtendMeld | Discard | Chin,
    Field(discriminator="type"),
]
