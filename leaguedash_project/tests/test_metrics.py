from pathlib import Path

import pandas as pd
import pytest

from leaguedash.mapper import ColumnMapper
from leaguedash.metrics.goals import GoalsPerMatchMetric
from leaguedash.metrics.registry import metric_registry
from leaguedash.metrics.standings import StandingsMetric
from leaguedash.metrics.streaks import StreaksMetric
from leaguedash.sources import CsvSource, JsonSource

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

RESULTS = [
    ("Arsenal", "Chelsea", 2, 1), ("Arsenal", "Liverpool", 3, 0), ("Arsenal", "Tottenham", 1, 1),
    ("Chelsea", "Arsenal", 0, 1), ("Chelsea", "Liverpool", 2, 2), ("Chelsea", "Tottenham", 3, 0),
    ("Liverpool", "Arsenal", 1, 2), ("Liverpool", "Chelsea", 1, 0), ("Liverpool", "Tottenham", 2, 1),
    ("Tottenham", "Arsenal", 0, 2), ("Tottenham", "Chelsea", 1, 1), ("Tottenham", "Liverpool", 0, 3),
]

EXPECTED_STANDINGS = pd.DataFrame(
    [
        ("Arsenal", 6, 5, 1, 0, 11, 3, 8, 16),
        ("Liverpool", 6, 3, 1, 2, 9, 8, 1, 10),
        ("Chelsea", 6, 1, 2, 3, 7, 7, 0, 5),
        ("Tottenham", 6, 0, 2, 4, 3, 12, -9, 2),
    ],
    columns=["team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"],
)


@pytest.fixture
def matches() -> pd.DataFrame:
    df = pd.DataFrame(RESULTS, columns=["home_team", "away_team", "home_goals", "away_goals"])
    return df.assign(
        match_id=range(len(df)),
        league="PL",
        season="2024-25",
        date=pd.date_range("2024-08-17", periods=len(df), freq="7D"),
    )


def _plain(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype({"team": object}).astype({c: "int64" for c in df.columns if c != "team"})


def test_standings_exact_values_and_order(matches: pd.DataFrame) -> None:
    result = StandingsMetric().compute(matches)
    assert list(result["team"]) == ["Arsenal", "Liverpool", "Chelsea", "Tottenham"]
    pd.testing.assert_frame_equal(_plain(result), EXPECTED_STANDINGS)


def test_standings_tiebreak_gd_then_gf_then_name() -> None:
    # A and B both 3 pts; B has better GD. C and D both 0 pts with equal GD/GF -> alphabetical.
    df = pd.DataFrame(
        [("A", "D", 1, 0), ("B", "C", 3, 0), ("C", "D", 0, 0)],
        columns=["home_team", "away_team", "home_goals", "away_goals"],
    )
    assert list(StandingsMetric().compute(df)["team"]) == ["B", "A", "D", "C"]


def test_streaks(matches: pd.DataFrame) -> None:
    result = StreaksMetric().compute(matches)
    expected = pd.DataFrame(
        [("Arsenal", 3, 3), ("Liverpool", 3, 3), ("Chelsea", 0, 1), ("Tottenham", 0, 0)],
        columns=["team", "current_streak", "longest_streak"],
    )
    pd.testing.assert_frame_equal(_plain(result), expected)


def test_streaks_respect_date_order_over_match_id(matches: pd.DataFrame) -> None:
    # Reverse the calendar: Arsenal's sequence becomes W,W,W,D,W,W -> current 2, longest 3.
    reversed_dates = matches.assign(date=matches["date"].iloc[::-1].to_numpy())
    result = StreaksMetric().compute(reversed_dates).set_index("team")
    assert result.loc["Arsenal", "current_streak"] == 2
    assert result.loc["Arsenal", "longest_streak"] == 3


def test_goals_per_match(matches: pd.DataFrame) -> None:
    result = GoalsPerMatchMetric().compute(matches).set_index("team")
    assert list(result.index) == ["Arsenal", "Chelsea", "Liverpool", "Tottenham"]
    arsenal = result.loc["Arsenal"]
    assert arsenal["home_scored"] == pytest.approx(2.0)
    assert arsenal["home_conceded"] == pytest.approx(2 / 3)
    assert arsenal["away_scored"] == pytest.approx(5 / 3)
    assert arsenal["away_conceded"] == pytest.approx(1 / 3)
    # Tottenham home: 0-2, 1-1, 0-3 ; away: 1-1, 0-3, 1-2
    assert result.loc["Tottenham", "home_scored"] == pytest.approx(1 / 3)
    assert result.loc["Tottenham", "home_conceded"] == pytest.approx(2.0)
    assert result.loc["Tottenham", "away_scored"] == pytest.approx(2 / 3)
    assert result.loc["Tottenham", "away_conceded"] == pytest.approx(2.0)
    assert result["league_avg_home"].unique() == pytest.approx([16 / 12])
    assert result["league_avg_away"].unique() == pytest.approx([14 / 12])


def test_metrics_are_pure(matches: pd.DataFrame) -> None:
    before = matches.copy()
    for metric_id in metric_registry.ids():
        metric_registry.get(metric_id).compute(matches)
    pd.testing.assert_frame_equal(matches, before)


def test_registry_lookup() -> None:
    assert metric_registry.ids() == ["standings", "streaks", "goals_per_match"]
    assert isinstance(metric_registry.get("standings"), StandingsMetric)


@pytest.mark.parametrize(
    ("source", "file_name"),
    [(CsvSource(), "sample_standard.csv"), (JsonSource(), "sample_nested.json")],
)
def test_samples_end_to_end(source: CsvSource | JsonSource, file_name: str) -> None:
    raw = source.read(SAMPLES / file_name)
    mapper = ColumnMapper()
    mapper.mapping = mapper.suggest(raw)
    result = mapper.apply(raw)
    assert result.skipped_rows == 0
    pd.testing.assert_frame_equal(_plain(StandingsMetric().compute(result.matches)), EXPECTED_STANDINGS)
    streaks = StreaksMetric().compute(result.matches).set_index("team")
    assert streaks.loc["Arsenal", "current_streak"] == 3
