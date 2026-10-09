from leaguedash.metrics.base import MetricRegistry
from leaguedash.metrics.goals import GoalsPerMatchMetric
from leaguedash.metrics.standings import StandingsMetric
from leaguedash.metrics.streaks import StreaksMetric

metric_registry = MetricRegistry()
metric_registry.register(StandingsMetric)
metric_registry.register(StreaksMetric)
metric_registry.register(GoalsPerMatchMetric)
