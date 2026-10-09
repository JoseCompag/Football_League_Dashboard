# leaguedash

Upload any football results file (CSV/JSON), map its columns once, get standings, streaks and goal charts.

## Run
```bash
pip install -r requirements.txt
python -m pytest tests/ -v
python -m streamlit run app/main.py   # then upload samples/sample_standard.csv or samples/sample_nested.json
```

## How to add a field
1. Open `leaguedash/schema.py`.
2. Add one `field_registry.register(FieldSchema(key, label, dtype, required, aliases))` line.
3. Done — it appears in the mapping sidebar, auto-suggestion and type coercion.

## How to add a metric
1. Create `leaguedash/metrics/<name>.py` with a `Metric` subclass: set `id`, implement pure `compute(matches) -> DataFrame`.
2. Add `metric_registry.register(YourMetric)` (plus its import) in `leaguedash/metrics/registry.py`.
3. Done — the dashboard shows it as a table; optionally add a `Widget` in `app/widgets.py` for a chart.
