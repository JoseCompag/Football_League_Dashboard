"""Streamlit orchestration: upload -> map -> filter -> metrics -> widgets."""

import pandas as pd
import streamlit as st

from app.widgets import ACCENT, WIDGETS
from leaguedash.mapper import ColumnMapper
from leaguedash.metrics.registry import metric_registry
from leaguedash.repository import MatchRepository
from leaguedash.schema import field_registry
from leaguedash.sources import CsvSource, DataSource, JsonSource

CSS = f"""<style>
.stApp h1, .stApp h2, .stApp h3 {{ color: {ACCENT}; font-weight: 600; }}
.block-container {{ padding-top: 2rem; }}
</style>"""


def _label(value: str | None) -> str:
    return "—" if value is None else str(value)


class Dashboard:
    def __init__(self) -> None:
        self.selected_team: str | None = None

    def run(self) -> None:
        st.set_page_config(page_title="League Dashboard", layout="wide")
        st.markdown(CSS, unsafe_allow_html=True)
        st.title("League Dashboard")

        upload = st.sidebar.file_uploader("Match file", type=["csv", "json"])
        if upload is None:
            st.info("Upload a CSV or JSON file of match results to begin (see `samples/`).")
            return
        try:
            raw = self._source(upload.name).read(upload)
        except (ValueError, KeyError) as exc:
            st.error(f"Could not read file: {exc}")
            return

        mapper = self._mapping(raw)
        errors = mapper.validate()
        if errors:
            st.warning("Complete the column mapping in the sidebar: " + "; ".join(errors))
            return
        result = mapper.apply(raw)
        for message in result.warnings:
            st.warning(message)

        repo = MatchRepository()
        repo.load(result)
        matches = repo.filter(*self._filters(repo.matches))
        if matches.empty:
            st.warning("No matches for the selected filters.")
            return

        teams = sorted(pd.unique(matches[["home_team", "away_team"]].to_numpy().ravel()))
        self.selected_team = st.sidebar.selectbox("Highlight team", [None, *teams], format_func=_label)
        self._downloads(repo, mapper)

        st.caption(f"{len(matches)} matches · {result.skipped_rows} skipped rows")
        columns = st.columns(2)
        for i, metric_id in enumerate(metric_registry.ids()):
            frame = metric_registry.get(metric_id).compute(matches)
            widget = WIDGETS.get(metric_id)
            with columns[i % 2]:
                st.subheader(widget.title if widget else metric_id.replace("_", " ").capitalize())
                if widget:
                    widget.render(frame, self.selected_team)
                else:
                    st.dataframe(frame, hide_index=True)

    @staticmethod
    def _source(file_name: str) -> DataSource:
        sources: list[DataSource] = [CsvSource(), JsonSource()]
        source = next(s for s in sources if s.can_handle(file_name))
        with st.sidebar.expander("File options"):
            if isinstance(source, CsvSource):
                source.sep = st.text_input("CSV separator", value=",") or ","
            elif isinstance(source, JsonSource):
                source.record_path = st.text_input("JSON record path (blank = auto)") or None
        return source

    @staticmethod
    def _mapping(raw: pd.DataFrame) -> ColumnMapper:
        with st.sidebar.expander("Column mapping", expanded=True):
            saved = st.file_uploader("Load saved mapping", type=["json"])
            defaults = ColumnMapper.from_json(saved.getvalue().decode()).mapping if saved else ColumnMapper().suggest(raw)
            options: list[str | None] = [None, *map(str, raw.columns)]
            mapping = {
                f.key: st.selectbox(
                    f"{f.label}{' *' if f.required else ''}", options, format_func=_label,
                    index=options.index(defaults.get(f.key)) if defaults.get(f.key) in options else 0,
                )
                for f in field_registry.all()
            }
        return ColumnMapper(mapping)

    @staticmethod
    def _filters(matches: pd.DataFrame) -> tuple[str | None, str | None]:
        def choose(column: str, label: str) -> str | None:
            if column not in matches.columns or matches[column].isna().all():
                return None
            values = sorted(matches[column].dropna().unique())
            return st.sidebar.selectbox(label, [None, *values], format_func=lambda v: "All" if v is None else v)

        return choose("league", "League"), choose("season", "Season")

    @staticmethod
    def _downloads(repo: MatchRepository, mapper: ColumnMapper) -> None:
        with st.sidebar.expander("Download"):
            st.download_button("Clean matches (CSV)", repo.export("csv"), "matches.csv", "text/csv")
            st.download_button("Clean matches (JSON)", repo.export("json"), "matches.json", "application/json")
            st.download_button("Column mapping (JSON)", mapper.to_json().encode(), "mapping.json", "application/json")
