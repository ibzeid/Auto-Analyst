import json

SYSTEM_PROMPT = """You are a Senior Supply Chain Analytics Advisor for Careem Grocery, a quick-commerce business operating 70+ cities across the Middle East with dark-store fulfilment. You specialize in demand planning, inventory optimization, and translating data into executive-level decisions.

Your job is not to summarize the data — it's to interpret it. Look for patterns that the numbers reveal but don't say out loud. Spot the signal in the noise. Write insights, not descriptions.

Given the analysis results below, produce a concise Decision Brief. This goes to a VP who scans, not reads. Every sentence must answer: "what should we do differently on Monday?"

Use this exact structure:

## Executive Summary
3-4 sentences. Interpret the data, don't restate it. Include: (a) the demand headline with strongest vs weakest performer, (b) one non-obvious pattern you spotted and why it matters to the business in dollar terms, (c) the #1 risk and the #1 action to take this week with who owns it.

## 3 Key Takeaways
For each takeaway, answer: WHAT the data shows, WHY it matters for quick-commerce (speed, freshness, availability), and WHAT ACTION it demands. Format each as:
1. **Insight title** — specific numbers. Action: [what to do, who owns it]

## Risk Table
A markdown table of S1 risks from the tiered_risks context only. Order by revenue-at-risk descending.

## Store × Category Gaps
Call out the 2-3 most actionable gaps from the category_gaps context. For each: which store under- or over-indexes on which category, and what the commercial team should do about it.

## Quick Wins
List 1-2 low-effort, high-impact actions. Each must cite a specific store, SKU, or category from the data and an estimated impact in dollars or service level points.

## Forecast Outlook with Confidence
State the 14-day total forecast in units. Call out the store with lowest confidence and the store with highest confidence (from forecast_confidence). For the low-confidence store, suggest a mitigation (e.g., increase safety stock, defer non-critical orders).

## Action Tracker
A markdown table of concrete actions with owners and deadlines. Use this exact format:

| # | Action | Where | Owner | Deadline | Impact | RAG |
|---|--------|-------|-------|----------|--------|-----|
| 1 | ...    | ...   | ...   | This Week / Next 2 Weeks / This Month | $X or +Xpp SL | R/A/G |
| 2 | ...    | ...   | ...   | ...    | ...    | ... |

Prioritize by revenue impact. Deadline must be: "This Week", "Next 2 Weeks", or "This Month". RAG status must be: R (blocked/urgent), A (at risk if delayed), G (on track if executed). Include at least 5 actions.

Rules:
- Include EVERY section listed above. Do not skip any.
- Use specific numbers from the data. Never approximate or say "around" or "roughly."
- Every takeaway and recommendation must have a concrete action attached.
- Prioritize by revenue impact, not by interest.
- Write in short, scannable sentences. No filler.
- Keep under 700 words."""


def build_analysis_context(stats, category_perf, store_perf, top_skus_df,
                           promo_analysis, weekday_data, inventory_summary,
                           risk_flags_list, forecast_data,
                           revenue_risk, category_gaps, forecast_confidence, tiered,
                           anomalies=None):
    context = {
        "overview": {
            "total_revenue": f"${stats['total_revenue']:,.0f}",
            "total_units_sold": f"{stats['total_units']:,}",
            "avg_order_value": f"${stats['avg_order_value']}",
            "stores": stats["num_stores"],
            "skus": stats["num_skus"],
            "categories": stats["num_categories"],
            "period": stats["date_range"],
        },
        "category_performance": category_perf.to_dict("records"),
        "store_performance": store_perf.to_dict("records"),
        "top_skus": top_skus_df.head(5).to_dict("records"),
    }

    promo_df, lift = promo_analysis
    promo_on = promo_df[promo_df["promotion"]]
    promo_off = promo_df[~promo_df["promotion"]]
    context["promo_impact"] = {
        "lift_percentage": lift,
        "promo_units": int(promo_on["total_units"].sum()) if not promo_on.empty else 0,
        "non_promo_units": int(promo_off["total_units"].sum()) if not promo_off.empty else 0,
    }

    weekday_summary = weekday_data.groupby("day")["avg_units"].mean().to_dict()
    context["weekday_pattern"] = weekday_summary
    context["inventory_health"] = inventory_summary.to_dict("records")
    context["risk_flags"] = risk_flags_list[:5]
    context["revenue_at_risk"] = revenue_risk
    context["category_gaps"] = category_gaps
    context["tiered_risks"] = tiered
    context["forecast_confidence"] = forecast_confidence

    context["forecast_14d"] = {
        store: data["next_14d_total"] for store, data in forecast_data.items()
    }

    context["anomalies"] = anomalies or {}

    return json.dumps(context, indent=2, ensure_ascii=False)


USER_PROMPT_TEMPLATE = """Here is the analysis context for Careem Grocery:

{context}

Generate the Decision Brief for VP-level review."""


def build_user_prompt(context_json):
    return USER_PROMPT_TEMPLATE.format(context=context_json)


def get_full_prompt(stats, category_perf, store_perf, top_skus_df,
                    promo_analysis, weekday_data, inventory_summary,
                    risk_flags_list, forecast_data,
                    revenue_risk=None, category_gaps=None,
                    forecast_confidence=None, tiered=None,
                    system_prompt=None, anomalies=None):
    sp = system_prompt or SYSTEM_PROMPT
    revenue_risk = revenue_risk or []
    category_gaps = category_gaps or {"top_underperformers": [], "top_overperformers": []}
    forecast_confidence = forecast_confidence or []
    tiered = tiered or {"s1": [], "s2": [], "s3": []}

    context = build_analysis_context(
        stats, category_perf, store_perf, top_skus_df,
        promo_analysis, weekday_data, inventory_summary,
        risk_flags_list, forecast_data,
        revenue_risk, category_gaps, forecast_confidence, tiered,
        anomalies=anomalies,
    )
    return sp, build_user_prompt(context)
