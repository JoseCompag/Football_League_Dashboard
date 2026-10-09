import pandas as pd

from leaguedash.metrics.base import Metric, long_format

COLUMNS = ["team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]


class StandingsMetric(Metric):
    id = "standings"

    def compute(self, matches: pd.DataFrame) -> pd.DataFrame:
        long = long_format(matches)
        long = long.assign(
            W=(long["gf"] > long["ga"]).astype(int),
            D=(long["gf"] == long["ga"]).astype(int),
            L=(long["gf"] < long["ga"]).astype(int),
        )
        table = long.groupby("team").agg(
            P=("gf", "count"), W=("W", "sum"), D=("D", "sum"), L=("L", "sum"),
            GF=("gf", "sum"), GA=("ga", "sum"),
        )
        table = table.assign(GD=table["GF"] - table["GA"], Pts=3 * table["W"] + table["D"]).reset_index()
        return table.sort_values(
            ["Pts", "GD", "GF", "team"], ascending=[False, False, False, True], ignore_index=True
        )[COLUMNS]
