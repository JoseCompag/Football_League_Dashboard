import pandas as pd

from leaguedash.metrics.base import Metric, long_format


class StreaksMetric(Metric):
    id = "streaks"

    def compute(self, matches: pd.DataFrame) -> pd.DataFrame:
        long = long_format(matches)
        order = ["team", *[c for c in ("date", "match_id") if c in long.columns]]
        long = long.sort_values(order, kind="stable", ignore_index=True)

        win = long["gf"] > long["ga"]
        run_id = win.ne(win.groupby(long["team"]).shift()).cumsum()  # new run on result change or new team
        runs = long.assign(win=win, run=run_id).groupby("run").agg(
            team=("team", "first"), win=("win", "first"), length=("win", "size")
        )

        last_run = runs.drop_duplicates("team", keep="last").set_index("team")
        longest = runs.loc[runs["win"]].groupby("team")["length"].max()
        result = pd.DataFrame({
            "current_streak": last_run["length"].where(last_run["win"], 0).astype(int),
            "longest_streak": longest.reindex(last_run.index, fill_value=0).astype(int),
        }).rename_axis("team").reset_index()
        return result.sort_values(["longest_streak", "team"], ascending=[False, True], ignore_index=True)
