
def run_scenario(df, forecast_data, inv_df, params):
    promo_mult = params.get("promo_mult", 1.0)
    demand_growth = params.get("demand_growth", 0.0)
    lead_time = params.get("lead_time", 3)
    safety_factor = params.get("safety_factor", 1.0)
    category_boost = params.get("category_boost", {})

    base_revenue = df["revenue"].sum()
    base_units = df["units_sold"].sum()
    base_stockout_rate = inv_df["stockout_days"].sum() / inv_df["total_days"].sum()

    adj_units = base_units * (1 + demand_growth / 100)
    adj_revenue = base_revenue * (1 + demand_growth / 100)

    promo_fraction = df["promotion"].mean()
    adj_units = adj_units * (1 + promo_fraction * (promo_mult - 1))

    cat_impact = {}
    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        cat_share = cat_df["revenue"].sum() / base_revenue
        boost = category_boost.get(cat, 0)
        cat_impact[cat] = {
            "base_revenue": round(cat_df["revenue"].sum(), 0),
            "projected_revenue": round(cat_df["revenue"].sum() * (1 + demand_growth / 100) * (1 + boost / 100), 0),
            "boost_pct": boost,
        }

    total_forecast = sum(d["next_14d_total"] for d in forecast_data.values())
    adj_forecast = total_forecast * (1 + demand_growth / 100) * (1 + promo_fraction * (promo_mult - 1))

    avg_daily_units = base_units / len(df["date"].unique())
    safety_stock_adj = avg_daily_units * lead_time * safety_factor

    result = {
        "params": params,
        "base": {
            "total_revenue": round(base_revenue, 0),
            "total_units": int(base_units),
            "stockout_rate": round(base_stockout_rate * 100, 1),
            "forecast_14d": int(total_forecast),
        },
        "projected": {
            "total_revenue": round(adj_revenue, 0),
            "total_units": int(adj_units),
            "stockout_rate": max(0, round((base_stockout_rate - (safety_factor - 1) * 0.01) * 100, 1)),
            "forecast_14d": int(adj_forecast),
            "safety_stock_days": round(safety_stock_adj, 0),
        },
        "delta": {
            "revenue_change": round(adj_revenue - base_revenue, 0),
            "revenue_change_pct": round(((adj_revenue / base_revenue) - 1) * 100, 1),
            "forecast_change_pct": round(((adj_forecast / total_forecast) - 1) * 100, 1),
        },
        "category_impact": cat_impact,
    }

    return result
