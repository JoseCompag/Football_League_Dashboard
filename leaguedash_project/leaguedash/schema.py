"""Canonical match fields. Adding a field = one `field_registry.register(...)` call below."""

from dataclasses import dataclass, field
from typing import Literal

DType = Literal["str", "int", "datetime"]


@dataclass(frozen=True)
class FieldSchema:
    key: str
    label: str
    dtype: DType
    required: bool
    aliases: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.dtype not in ("str", "int", "datetime"):
            raise ValueError(f"Unsupported dtype {self.dtype!r} for field {self.key!r}")


class FieldRegistry:
    def __init__(self) -> None:
        self._fields: dict[str, FieldSchema] = {}

    def register(self, field: FieldSchema) -> None:
        if field.key in self._fields:
            raise ValueError(f"Field {field.key!r} is already registered")
        self._fields[field.key] = field

    def all(self) -> list[FieldSchema]:
        return list(self._fields.values())

    def required(self) -> list[FieldSchema]:
        return [f for f in self._fields.values() if f.required]


field_registry = FieldRegistry()
field_registry.register(FieldSchema("league", "League", "str", False, ["league_name", "competition", "league.name"]))
field_registry.register(FieldSchema("season", "Season", "str", False, ["season_name", "year", "season.name"]))
field_registry.register(FieldSchema("date", "Date", "datetime", False, ["match_date", "date_played", "matchday"]))
field_registry.register(FieldSchema("home_team", "Home Team", "str", True, ["hometeam", "home", "home_team_name"]))
field_registry.register(FieldSchema("away_team", "Away Team", "str", True, ["awayteam", "away", "away_team_name"]))
field_registry.register(FieldSchema("home_goals", "Home Goals", "int", True, ["hgoals", "home_score", "fthg", "home_goals_ft"]))
field_registry.register(FieldSchema("away_goals", "Away Goals", "int", True, ["agoals", "away_score", "ftag", "away_goals_ft"]))
