"""Streamlit/Plotly renderers, one per metric id."""

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ACCENT = "#1B6B4A"
MUTED = "#C9CDD2"


def _is_selected(teams: pd.Series, selected_team: str | None) -> np.ndarray:
    """NA-safe boolean mask (team columns use the nullable "string" dtype)."""
    return teams.eq(selected_team).fillna(False).to_numpy(dtype=bool)


def _base_layout(fig: go.Figure, height: int) -> go.Figure:
    return fig.update_layout(
        template="simple_white", height=height, margin=dict(l=10, r=10, t=10, b=10),
        font=dict(size=13), showlegend=False,
    )


class Widget(ABC):
    metric_id: ClassVar[str]
    title: ClassVar[str]

    @abstractmethod
    def render(self, result: pd.DataFrame, selected_team: str | None) -> None: ...


class StandingsTable(Widget):
    metric_id = "standings"
    title = "Standings"

    def render(self, result: pd.DataFrame, selected_team: str | None) -> None:
        def highlight(df: pd.DataFrame) -> pd.DataFrame:
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            styles.loc[_is_selected(df["team"], selected_team), :] = f"background-color: {ACCENT}; color: white"
            return styles

        st.dataframe(result.style.apply(highlight, axis=None), hide_index=True)


class StreakChart(Widget):
    metric_id = "streaks"
    title = "Longest winning streak"

    def render(self, result: pd.DataFrame, selected_team: str | None) -> None:
        fig = go.Figure(go.Bar(
            x=result["longest_streak"], y=result["team"], orientation="h",
            marker_color=np.where(_is_selected(result["team"], selected_team) | (selected_team is None), ACCENT, MUTED),
            text="current " + result["current_streak"].astype(str), textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{x} wins<extra></extra>",
        ))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(title="wins in a row", dtick=1, range=[0, result["longest_streak"].max() + 1.2])
        st.plotly_chart(_base_layout(fig, height=60 + 36 * len(result)))


class GoalsChart(Widget):
    metric_id = "goals_per_match"
    title = "Goals scored per match"

    def render(self, result: pd.DataFrame, selected_team: str | None) -> None:
        opacity = np.where(_is_selected(result["team"], selected_team) | (selected_team is None), 1.0, 0.35)
        fig = go.Figure([
            go.Bar(name="Home", x=result["team"], y=result["home_scored"], marker=dict(color=ACCENT, opacity=opacity)),
            go.Bar(name="Away", x=result["team"], y=result["away_scored"], marker=dict(color=MUTED, opacity=opacity)),
        ])
        fig.add_hline(y=result["league_avg_home"].iat[0], line_dash="dot", line_width=1.5, line_color=ACCENT,
                      annotation_text="league avg home", annotation_position="top right")
        fig.add_hline(y=result["league_avg_away"].iat[0], line_dash="dot", line_width=1.5, line_color="#8A9096",
                      annotation_text="league avg away", annotation_position="bottom right")
        fig.update_traces(hovertemplate="%{x}: %{y:.2f}<extra>%{fullData.name}</extra>")
        _base_layout(fig, height=360).update_layout(barmode="group", showlegend=True,
                                                    legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig)


WIDGETS: dict[str, Widget] = {w.metric_id: w for w in (StandingsTable(), StreakChart(), GoalsChart())}
