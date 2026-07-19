from analysis.stats import (
    summary_stats,
    category_performance,
    store_performance,
    top_skus,
    promo_impact,
    weekday_pattern,
    revenue_at_risk,
    store_category_gaps,
)
from analysis.forecast import (
    simple_forecast,
    forecast_all_stores,
    forecast_by_category,
    forecast_confidence_summary,
)
from analysis.inventory import (
    inventory_health,
    risk_flags,
    tiered_risks,
    category_inventory_summary,
)
from analysis.scorecard import rag_scorecard
from analysis.scenario import run_scenario
from analysis.anomaly import detect_anomalies
