import pandas as pd

from leaguedash.metrics.base import Metric


class GoalsPerMatchMetric(Metric):
    id = "goals_per_match"

    def compute(self, matches: pd.DataFrame) -> pd.DataFrame:
        home = matches.groupby("home_team").agg(
            home_scored=("home_goals", "mean"), home_conceded=("away_goals", "mean")
        ).rename_axis("team").reset_index()
        away = matches.groupby("away_team").agg(
            away_scored=("away_goals", "mean"), away_conceded=("home_goals", "mean")
        ).rename_axis("team").reset_index()
        result = home.merge(away, on="team", how="outer").assign(
            league_avg_home=matches["home_goals"].mean(),
            league_avg_away=matches["away_goals"].mean(),
        )
        return result.sort_values("team", ignore_index=True)
