import pandas as pd
import pytest

from leaguedash.mapper import ColumnMapper
from leaguedash.repository import MatchRepository


def test_suggest_uses_key_and_aliases_case_insensitively() -> None:
    df = pd.DataFrame(columns=["Div", "Season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    assert ColumnMapper().suggest(df) == {
        "league": None,  # "Div" is not a registered alias
        "season": "Season",
        "date": "Date",
        "home_team": "HomeTeam",
        "away_team": "AwayTeam",
        "home_goals": "FTHG",
        "away_goals": "FTAG",
    }


def test_suggest_dotted_nested_columns() -> None:
    df = pd.DataFrame(columns=["league.name", "season.name", "date_played", "home", "away", "home_score", "away_score"])
    suggestion = ColumnMapper().suggest(df)
    assert suggestion["league"] == "league.name"
    assert suggestion["season"] == "season.name"
    assert suggestion["home_goals"] == "home_score"


def test_validate_reports_missing_required() -> None:
    errors = ColumnMapper({"home_team": "h", "away_team": "a", "home_goals": "hg"}).validate()
    assert errors == ["Required field 'Away Goals' is not mapped"]
    with pytest.raises(ValueError):
        ColumnMapper({}).apply(pd.DataFrame())


def test_apply_coerces_drops_and_keeps_match_id() -> None:
    raw = pd.DataFrame({
        "H": ["Arsenal", " Chelsea ", "Liverpool", "Spurs"],
        "A": ["Chelsea", "Arsenal", "Spurs", "Liverpool"],
        "HG": ["2", "x", "1", None],
        "AG": [1, 0, 1, 2],
        "When": ["2024-08-17", "2024-08-24", "not a date", "2024-09-07"],
        "Ignored": [1, 2, 3, 4],
    })
    mapper = ColumnMapper({"home_team": "H", "away_team": "A", "home_goals": "HG", "away_goals": "AG", "date": "When"})
    result = mapper.apply(raw)

    assert result.skipped_rows == 2
    assert list(result.matches.columns) == ["match_id", "date", "home_team", "away_team", "home_goals", "away_goals"]
    assert list(result.matches["match_id"]) == [0, 2]
    assert result.matches["home_goals"].dtype == "int64"
    assert pd.api.types.is_datetime64_any_dtype(result.matches["date"])
    assert result.matches["date"].isna().tolist() == [False, True]
    assert len(result.warnings) == 2


def test_json_round_trip() -> None:
    mapper = ColumnMapper({"home_team": "HomeTeam", "league": None})
    restored = ColumnMapper.from_json(mapper.to_json())
    assert restored.mapping == mapper.mapping


def test_repository_filter_and_export() -> None:
    raw = pd.DataFrame({"h": ["A", "B"], "a": ["B", "A"], "hg": [1, 2], "ag": [0, 2], "s": ["2023", "2024"]})
    repo = MatchRepository()
    repo.load(ColumnMapper({"home_team": "h", "away_team": "a", "home_goals": "hg", "away_goals": "ag", "season": "s"}).apply(raw))
    assert len(repo.filter(season="2024")) == 1
    assert len(repo.filter(league="PL")) == 2  # no league column -> ignored
    assert repo.export("csv").decode().startswith("match_id,season,home_team")
    assert b'"home_team":"A"' in repo.export("json").replace(b" ", b"")
    with pytest.raises(ValueError):
        repo.export("xml")
