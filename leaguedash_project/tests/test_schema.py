import pandas as pd
import pytest

from leaguedash.mapper import ColumnMapper
from leaguedash.schema import FieldRegistry, FieldSchema, field_registry


def test_all_fields_registered() -> None:
    keys = [f.key for f in field_registry.all()]
    assert keys == ["league", "season", "date", "home_team", "away_team", "home_goals", "away_goals"]


def test_required_fields() -> None:
    assert [f.key for f in field_registry.required()] == ["home_team", "away_team", "home_goals", "away_goals"]


def test_adding_referee_field_flows_into_mapper() -> None:
    registry = FieldRegistry()
    for f in field_registry.all():
        registry.register(f)
    registry.register(FieldSchema("referee", "Referee", "str", False, ["ref", "official"]))

    assert len(registry.all()) == 8
    assert len(registry.required()) == 4
    df = pd.DataFrame(columns=["HomeTeam", "AwayTeam", "FTHG", "FTAG", "Official"])
    assert ColumnMapper(registry=registry).suggest(df)["referee"] == "Official"


def test_duplicate_and_invalid_fields_rejected() -> None:
    with pytest.raises(ValueError):
        field_registry.register(FieldSchema("league", "League", "str", False))
    with pytest.raises(ValueError):
        FieldSchema("x", "X", "float", False)  # type: ignore[arg-type]
