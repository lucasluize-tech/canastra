"""Engine state models (pydantic v2).

These are serializable value objects. No behavior lives here — logic is
in canastra/engine/engine.py and canastra/engine/scoring.py. All models
are frozen so handlers must explicitly rebuild state when they change
it (no accidental in-place mutation).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
