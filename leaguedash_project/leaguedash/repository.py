"""In-memory store of cleaned, canonical matches."""

import pandas as pd

from leaguedash.mapper import MappingResult


class MatchRepository:
    def __init__(self) -> None:
        self.matches: pd.DataFrame = pd.DataFrame()

    def load(self, result: MappingResult) -> None:
        self.matches = result.matches

    def filter(self, league: str | None = None, season: str | None = None) -> pd.DataFrame:
        mask = pd.Series(True, index=self.matches.index)
        for column, value in (("league", league), ("season", season)):
            if value is not None and column in self.matches.columns:
                mask &= self.matches[column].eq(value).fillna(False)
        return self.matches[mask]

    def export(self, fmt: str) -> bytes:
        if fmt == "csv":
            return self.matches.to_csv(index=False).encode("utf-8")
        if fmt == "json":
            return self.matches.to_json(orient="records", date_format="iso", indent=2).encode("utf-8")
        raise ValueError(f"Unsupported export format {fmt!r}; use 'csv' or 'json'")
