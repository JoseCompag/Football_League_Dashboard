"""Metric contract, registry, and the shared team-perspective (long) reshape."""

from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd


class Metric(ABC):
    id: ClassVar[str]

    @abstractmethod
    def compute(self, matches: pd.DataFrame) -> pd.DataFrame:
        """Pure function of the canonical matches frame."""


class MetricRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, type[Metric]] = {}

    def register(self, metric: type[Metric]) -> None:
        self._metrics[metric.id] = metric

    def get(self, id: str) -> Metric:
        return self._metrics[id]()

    def ids(self) -> list[str]:
        return list(self._metrics)


def long_format(matches: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match: one from the home team's perspective, one from the away team's."""
    extra = matches[[c for c in ("match_id", "date") if c in matches.columns]]
    home = extra.assign(
        team=matches["home_team"], opponent=matches["away_team"],
        gf=matches["home_goals"], ga=matches["away_goals"], is_home=True,
    )
    away = extra.assign(
        team=matches["away_team"], opponent=matches["home_team"],
        gf=matches["away_goals"], ga=matches["home_goals"], is_home=False,
    )
    return pd.concat([home, away], ignore_index=True)
