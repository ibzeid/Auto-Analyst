import pandas as pd


def detect_anomalies(df, z_threshold=2.5):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    daily = df.groupby("date").agg(
        total_units=("units_sold", "sum"),
        total_revenue=("revenue", "sum"),
    ).reset_index().sort_values("date")

    mean_units = daily["total_units"].mean()
    std_units = daily["total_units"].std()
    mean_rev = daily["total_revenue"].mean()
    std_rev = daily["total_revenue"].std()

    daily["z_units"] = (daily["total_units"] - mean_units) / std_units
    daily["z_revenue"] = (daily["total_revenue"] - mean_rev) / std_rev
    daily["is_anomaly"] = (daily["z_units"].abs() > z_threshold) | (daily["z_revenue"].abs() > z_threshold)
    daily["direction"] = daily.apply(
        lambda r: "spike" if r["total_units"] > mean_units else "dip"
        if r["is_anomaly"] else "normal", axis=1,
    )

    anomalies = daily[daily["is_anomaly"]].copy()
    anomalies["description"] = [
        _describe(r, mean_units, mean_rev) for _, r in anomalies.iterrows()
    ]

    top_anomalies = anomalies.sort_values("z_units", key=abs, ascending=False).head(8)

    return {
        "total_anomalous_days": int(daily["is_anomaly"].sum()),
        "anomaly_rate": round(daily["is_anomaly"].mean() * 100, 1),
        "top_anomalies": [
            {
                "date": str(r["date"].date()),
                "units": int(r["total_units"]),
                "revenue": round(r["total_revenue"], 0),
                "direction": r["direction"],
                "z_score": round(r["z_units"], 1),
                "description": r["description"],
            }
            for _, r in top_anomalies.iterrows()
        ],
        "recent_flag": int(daily.tail(7)["is_anomaly"].sum()) > 0,
    }


def _describe(r, mean, mean_rev):
    pct_dev = round(abs((r["total_units"] / mean) - 1) * 100)
    direction = "above" if r["total_units"] > mean else "below"
    return f"{r['direction'].title()} — {pct_dev}% {direction} daily average ({r['total_units']:,} units, ${r['total_revenue']:,.0f})"
