import numpy as np
import pandas as pd


def inventory_health(df):
    sku_stats = df.groupby(["store", "sku", "category"]).agg(
        daily_avg_units=("units_sold", "mean"),
        daily_std=("units_sold", "std"),
        stockout_days=("stockout", "sum"),
        total_days=("stockout", "count"),
        total_revenue=("revenue", "sum"),
    ).reset_index()

    sku_stats["service_level"] = (
        1 - sku_stats["stockout_days"] / sku_stats["total_days"]
    ).round(3)
    sku_stats["daily_avg_units"] = sku_stats["daily_avg_units"].round(1)
    sku_stats["daily_std"] = sku_stats["daily_std"].fillna(0).round(1)
    sku_stats["safety_stock"] = (
        sku_stats["daily_std"] * 1.96 * np.sqrt(3)
    ).round(0).astype(int)

    sku_stats["reorder_point"] = (
        sku_stats["daily_avg_units"] * 3 + sku_stats["safety_stock"]
    ).round(0).astype(int)

    sku_stats["revenue_per_day"] = sku_stats["total_revenue"] / sku_stats["total_days"]
    sku_stats["revenue_at_risk"] = (
        sku_stats["revenue_per_day"] * sku_stats["stockout_days"]
    )

    return sku_stats.sort_values("stockout_days", ascending=False)


def risk_flags(inv_df, service_level_threshold=0.95):
    low_service = inv_df[inv_df["service_level"] < service_level_threshold].copy()
    high_stockout = inv_df[inv_df["stockout_days"] > 3].copy()

    flags = []
    for _, row in low_service.iterrows():
        flags.append({
            "store": row["store"],
            "sku": row["sku"],
            "category": row["category"],
            "risk": "low_service_level",
            "metric": f"{row['service_level']:.1%}",
            "detail": f"Service level below {service_level_threshold:.0%} threshold",
        })

    for _, row in high_stockout.iterrows():
        flags.append({
            "store": row["store"],
            "sku": row["sku"],
            "category": row["category"],
            "risk": "high_stockout",
            "metric": f"{int(row['stockout_days'])} days",
            "detail": f"Stocked out on {int(row['stockout_days'])} of {int(row['total_days'])} days",
        })

    return flags


def tiered_risks(inv_df):
    risky = inv_df[inv_df["stockout_days"] > 0].copy()
    if risky.empty:
        return {"s1": [], "s2": [], "s3": []}

    risky["revenue_at_risk"] = risky["revenue_at_risk"].round(0)

    s1 = []
    s2 = []
    s3 = []

    for _, row in risky.sort_values("revenue_at_risk", ascending=False).iterrows():
        revenue_impact = row["revenue_at_risk"]
        stockout_days = int(row["stockout_days"])
        service_level = row["service_level"]

        if revenue_impact > 5000 or stockout_days > 10 or service_level < 0.80:
            tier = "S1"
            s1.append(_format_risk(row, tier))
        elif revenue_impact > 1000 or stockout_days > 5 or service_level < 0.90:
            tier = "S2"
            s2.append(_format_risk(row, tier))
        else:
            tier = "S3"
            s3.append(_format_risk(row, tier))

    return {"s1": s1[:5], "s2": s2[:5], "s3": s3[:3]}


def _format_risk(row, tier):
    revenue_impact = row["revenue_at_risk"]
    urgency = "Now" if tier == "S1" else "Next 7 days" if tier == "S2" else "Next 30 days"
    return {
        "store": row["store"],
        "sku": row["sku"],
        "category": row["category"],
        "tier": tier,
        "revenue_at_risk": f"${revenue_impact:,.0f}",
        "stockout_days": int(row["stockout_days"]),
        "service_level": f"{row['service_level']:.1%}",
        "urgency": urgency,
    }


def category_inventory_summary(inv_df):
    summary = inv_df.groupby("category").agg(
        avg_service_level=("service_level", "mean"),
        avg_safety_stock=("safety_stock", "mean"),
        total_stockout_days=("stockout_days", "sum"),
        total_revenue_at_risk=("revenue_at_risk", "sum"),
        skus_at_risk=("service_level", lambda x: (x < 0.95).sum()),
    ).reset_index()
    summary["avg_service_level"] = (summary["avg_service_level"] * 100).round(1)
    summary["total_revenue_at_risk"] = summary["total_revenue_at_risk"].round(0)
    return summary.sort_values("avg_service_level")
