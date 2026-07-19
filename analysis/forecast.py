import pandas as pd


def simple_forecast(series, window=14, forecast_days=14):
    series = pd.Series(series)
    if len(series) < window:
        return None
    smoothed = series.rolling(window=window, min_periods=1).mean()
    last_avg = smoothed.iloc[-window:].mean()
    recent_trend = series.iloc[-window:] - smoothed.iloc[-window:]
    avg_trend = recent_trend.mean()
    forecast = [max(0, last_avg + avg_trend * (i + 1)) for i in range(forecast_days)]
    recent_std = series.iloc[-window:].std()
    return {"values": forecast, "std": recent_std}


def forecast_all_stores(df, forecast_days=14):
    results = {}
    for store in df["store"].unique():
        store_df = df[df["store"] == store].copy()
        daily = store_df.groupby("date")["units_sold"].sum().reset_index()
        daily = daily.sort_values("date")
        fc = simple_forecast(daily["units_sold"].values, window=14, forecast_days=forecast_days)
        fc_values = fc["values"] if fc else None
        fc_std = fc["std"] if fc else 0
        results[store] = {
            "historical": daily,
            "forecast": fc_values,
            "next_14d_total": int(round(sum(fc_values))) if fc_values else 0,
            "daily_volatility": round(fc_std, 1),
            "confidence": _confidence_tier(fc_std, daily["units_sold"].mean()),
            "low_estimate": None if not fc_values else int(round(sum(fc_values) - 2 * fc_std * forecast_days)),
            "high_estimate": None if not fc_values else int(round(sum(fc_values) + 2 * fc_std * forecast_days)),
        }
    return results


def forecast_by_category(df, store, forecast_days=14):
    store_df = df[df["store"] == store].copy()
    results = {}
    for cat in store_df["category"].unique():
        cat_df = store_df[store_df["category"] == cat]
        daily = cat_df.groupby("date")["units_sold"].sum().reset_index()
        daily = daily.sort_values("date")
        fc = simple_forecast(daily["units_sold"].values, window=14, forecast_days=forecast_days)
        fc_values = fc["values"] if fc else None
        results[cat] = {
            "forecast": fc_values,
            "next_14d_total": int(round(sum(fc_values))) if fc_values else 0,
        }
    return results


def _confidence_tier(std, mean):
    if mean == 0 or std == 0:
        return "medium"
    cv = std / mean
    if cv < 0.10:
        return "high"
    elif cv < 0.25:
        return "medium"
    else:
        return "low"


def forecast_confidence_summary(forecast_data):
    conf = []
    for store, data in forecast_data.items():
        volat = data.get("daily_volatility", 0)
        conf.append({
            "store": store,
            "confidence": data.get("confidence", "medium"),
            "daily_volatility": volat,
            "range_14d": f"{data.get('low_estimate', 'N/A'):,} – {data.get('high_estimate', 'N/A'):,}"
            if data.get("low_estimate") is not None else "N/A",
        })
    return sorted(conf, key=lambda x: x["daily_volatility"], reverse=True)
