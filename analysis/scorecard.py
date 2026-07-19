def rag_scorecard(inv_df, cat_perf, store_perf):
    rag = []

    for _, row in inv_df.iterrows():
        sl = row["service_level"]
        so = int(row["stockout_days"])
        rev_at_risk = row.get("revenue_at_risk", 0)

        if sl >= 0.97 and so == 0:
            status = "GREEN"
        elif sl >= 0.90 and so <= 3:
            status = "AMBER"
        else:
            status = "RED"

        rag.append({
            "store": row["store"],
            "sku": row["sku"],
            "category": row["category"],
            "status": status,
            "service_level": round(sl * 100, 1),
            "stockout_days": so,
            "revenue_at_risk": round(rev_at_risk, 0),
        })

    summary = {}
    for store in inv_df["store"].unique():
        store_items = [r for r in rag if r["store"] == store]
        total = len(store_items)
        red = len([r for r in store_items if r["status"] == "RED"])
        amber = len([r for r in store_items if r["status"] == "AMBER"])
        green = len([r for r in store_items if r["status"] == "GREEN"])
        summary[store] = {
            "total": total,
            "red": red,
            "amber": amber,
            "green": green,
            "health_pct": round(green / total * 100, 0) if total else 0,
            "items": sorted(store_items, key=lambda x: x["revenue_at_risk"], reverse=True),
        }

    return {"items": rag, "summary": summary}
