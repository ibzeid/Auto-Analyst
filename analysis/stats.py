def summary_stats(df):
    stats = {
        "total_revenue": round(df["revenue"].sum(), 2),
        "total_units": int(df["units_sold"].sum()),
        "total_orders": int(len(df)),
        "avg_order_value": round(df["revenue"].sum() / len(df), 2),
        "date_range": f"{df['date'].min()} → {df['date'].max()}",
        "num_stores": df["store"].nunique(),
        "num_skus": df["sku"].nunique(),
        "num_categories": df["category"].nunique(),
    }
    return stats


def category_performance(df):
    cat = df.groupby("category").agg(
        total_revenue=("revenue", "sum"),
        total_units=("units_sold", "sum"),
        avg_daily_units=("units_sold", "mean"),
        stockout_rate=("stockout", "mean"),
        promo_frequency=("promotion", "mean"),
    ).reset_index()
    cat["stockout_rate"] = cat["stockout_rate"].round(4)
    cat["promo_frequency"] = cat["promo_frequency"].round(4)
    cat["avg_daily_units"] = cat["avg_daily_units"].round(1)
    cat["revenue_share"] = (cat["total_revenue"] / cat["total_revenue"].sum() * 100).round(1)
    return cat.sort_values("total_revenue", ascending=False)


def store_performance(df):
    stores = df.groupby("store").agg(
        total_revenue=("revenue", "sum"),
        total_units=("units_sold", "sum"),
        stockout_rate=("stockout", "mean"),
        avg_units_per_day=("units_sold", "mean"),
    ).reset_index()
    stores["stockout_rate"] = stores["stockout_rate"].round(4)
    stores["avg_units_per_day"] = stores["avg_units_per_day"].round(1)
    stores["revenue_share"] = (stores["total_revenue"] / stores["total_revenue"].sum() * 100).round(1)
    return stores.sort_values("total_revenue", ascending=False)


def top_skus(df, n=10):
    top = df.groupby(["sku", "category"]).agg(
        total_units=("units_sold", "sum"),
        total_revenue=("revenue", "sum"),
        avg_price=("price", "mean"),
        stockout_rate=("stockout", "mean"),
    ).reset_index()
    top["avg_price"] = top["avg_price"].round(2)
    top["stockout_rate"] = top["stockout_rate"].round(4)
    return top.sort_values("total_revenue", ascending=False).head(n)


def promo_impact(df):
    promo = df.groupby("promotion").agg(
        avg_units=("units_sold", "mean"),
        total_units=("units_sold", "sum"),
        total_revenue=("revenue", "sum"),
    ).reset_index()
    promo.columns = ["promotion", "avg_units_sold", "total_units", "total_revenue"]

    non_promo = promo[~promo["promotion"]]["avg_units_sold"].values
    promo_val = promo[promo["promotion"]]["avg_units_sold"].values

    if len(non_promo) > 0 and len(promo_val) > 0:
        lift_pct = round((promo_val[0] / non_promo[0] - 1) * 100, 1)
    else:
        lift_pct = 0.0

    return promo, lift_pct


def weekday_pattern(df):
    dow_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    pattern = df.groupby("day_of_week").agg(
        avg_units=("units_sold", "mean"),
        total_revenue=("revenue", "sum"),
    ).reset_index()
    pattern["day"] = pattern["day_of_week"].map(dow_map)
    return pattern.sort_values("day_of_week")


def stockout_analysis(df):
    stockouts = df[df["stockout"]].groupby(["category"]).agg(
        stockout_events=("stockout", "count"),
        lost_revenue=("revenue", "sum"),
    ).reset_index()
    total = df.groupby("category").agg(
        total_events=("stockout", "count"),
    ).reset_index()
    merged = stockouts.merge(total, on="category")
    merged["stockout_rate"] = (merged["stockout_events"] / merged["total_events"] * 100).round(1)
    return merged.sort_values("stockout_rate", ascending=False)


def revenue_at_risk(inv_df):
    risky = inv_df[inv_df["stockout_days"] > 0].copy()
    if risky.empty:
        return []
    risky["revenue_per_day"] = risky["total_revenue"] / risky["total_days"]
    risky["revenue_at_risk"] = risky["revenue_per_day"] * risky["stockout_days"]
    return [
        {
            "store": row["store"],
            "sku": row["sku"],
            "category": row["category"],
            "revenue_at_risk": round(row["revenue_at_risk"], 0),
            "stockout_days": int(row["stockout_days"]),
        }
        for _, row in risky.sort_values("revenue_at_risk", ascending=False).head(10).iterrows()
    ]


def store_category_gaps(df):
    by_store_cat = df.groupby(["store", "category"]).agg(
        store_cat_revenue=("revenue", "sum"),
    ).reset_index()
    store_total = df.groupby("store").agg(store_total=("revenue", "sum")).reset_index()
    cat_total = df.groupby("category").agg(cat_total=("revenue", "sum")).reset_index()
    overall = df["revenue"].sum()

    merged = by_store_cat.merge(store_total, on="store").merge(cat_total, on="category")
    merged["expected_share"] = merged["cat_total"] / overall
    merged["actual_share"] = merged["store_cat_revenue"] / merged["store_total"]
    merged["gap_pct"] = ((merged["actual_share"] - merged["expected_share"]) * 100).round(1)

    gaps = merged.sort_values("gap_pct")
    underperformers = gaps.head(5)
    overperformers = gaps.tail(5)

    return {
        "top_underperformers": [
            {
                "store": row["store"],
                "category": row["category"],
                "gap": f"{row['gap_pct']:+.1f}pp",
                "detail": f"Share is {row['gap_pct']:+.1f}pp vs. expected",
            }
            for _, row in underperformers.sort_values("gap_pct").iterrows()
        ],
        "top_overperformers": [
            {
                "store": row["store"],
                "category": row["category"],
                "gap": f"{row['gap_pct']:+.1f}pp",
                "detail": f"Share is {row['gap_pct']:+.1f}pp vs. expected",
            }
            for _, row in overperformers.sort_values("gap_pct", ascending=False).iterrows()
        ],
    }
