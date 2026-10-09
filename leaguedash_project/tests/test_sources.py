import io
import json
from pathlib import Path

import pytest

from leaguedash.sources import CsvSource, JsonSource

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_can_handle_by_extension() -> None:
    assert CsvSource().can_handle("results.CSV")
    assert not CsvSource().can_handle("results.json")
    assert JsonSource().can_handle(Path("results.json"))
    assert not JsonSource().can_handle("results.csv")


def test_csv_source_reads_csv() -> None:
    df = CsvSource().read(SAMPLES / "sample_standard.csv")
    assert df.shape == (12, 7)
    assert list(df.columns) == ["Div", "Season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]


def test_csv_source_custom_separator() -> None:
    df = CsvSource(sep=";").read(io.StringIO("home;away;hgoals;agoals\nA;B;1;0\n"))
    assert list(df.columns) == ["home", "away", "hgoals", "agoals"]


def test_json_source_flattens_nested_keys_and_detects_record_path() -> None:
    df = JsonSource().read(SAMPLES / "sample_nested.json")
    assert len(df) == 12
    assert {"league.name", "season.name", "date_played", "home", "away", "home_score", "away_score"} == set(df.columns)
    assert df.loc[0, "league.name"] == "PL"


def test_json_source_explicit_record_path_and_ambiguity() -> None:
    payload = {"games": [{"home": "A", "away": "B"}], "meta": [1, 2]}
    assert len(JsonSource(record_path="games").read(io.StringIO(json.dumps(payload)))) == 1
    with pytest.raises(ValueError):
        JsonSource().read(io.StringIO(json.dumps(payload)))
