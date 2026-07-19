"""Chat-based S&OP Analyst for Careem Grocery Auto-Analyst."""

import json

import altair as alt
import httpx
import pandas as pd

from insights.agents import CAREEM_PROMPT as CHAT_SYSTEM_PROMPT

alt.data_transformers.enable("default")

CAREEM_ISMS = [
    "Trust Allah but tie your camel — and by camel I mean your safety stock.",
    "A stockout in a top store is like a camel at a horse race — everyone notices.",
    "The best forecast is yesterday's demand plus a bit extra. But I'm paid to do better.",
    "Inventory without a forecast is just expensive furniture.",
    "The desert teaches patience. Supply chain teaches you to ignore that lesson.",
    "Good inventory is invisible. Bad inventory is tonight's emergency meeting.",
    "Revenue at risk is just a polite way of saying 'money you already lost'.",
    "In grocery, if you're not predicting the weekend rush by Tuesday, you're already late.",
    "I've been doing this 12 years. My gut has a better accuracy rate than most spreadsheets.",
    "A surplus is a future promotion. A shortage is a present disaster.",
    "Dairy doesn't negotiate deadlines. Yogurt goes bad whether you're ready or not.",
    "Forecasts are like directions in the desert: they point the way, but you still watch where you step.",
    "The hardest supply chain problem in Dubai isn't logistics — it's the AC in the warehouse.",
    "I've seen demand spikes during Ramadan that made a bakery's entire team quit for the day.",
    "Every QR1 of inventory sitting idle is a conversation you should have had last week.",
    "Quick-commerce means quick decisions. The data is here — the courage has to be yours.",
]

SIGNOFFS = [
    "Over and out, Captain.",
    "Back to you, boss.",
    "Khalas. What's next?",
    "Yalla, let's fix this.",
    "That's what I've got. Captain.",
    "Shoukran for asking — now go check your inventory.",
    "Careem out.",
]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_plot",
            "description": (
                "Generate an actual chart/plot to visualize supply chain data. "
                "Call this whenever the user asks to 'see', 'show', 'plot', 'chart', "
                "or 'visualize' data. Generate the chart, then write your analysis "
                "around it — the chart will render automatically below your text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["line", "bar", "scatter"],
                        "description": "Chart type: line for trends over time, bar for comparisons, scatter for "
                                       "correlations.",
                    },
                    "data_scope": {
                        "type": "string",
                        "enum": [
                            "revenue_trend",
                            "demand_trend",
                            "revenue_by_category",
                            "revenue_by_store",
                            "stockout_by_category",
                            "stockout_by_store",
                            "service_level",
                            "forecast",
                            "revenue_at_risk",
                            "top_skus",
                        ],
                        "description": (
                            "What to visualize. revenue_trend = daily revenue line. "
                            "demand_trend = daily units line. "
                            "revenue_by_category = revenue bars per category. "
                            "revenue_by_store = revenue bars per store. "
                            "stockout_by_category = stockout rate bars per category. "
                            "stockout_by_store = stockout rate bars per store. "
                            "service_level = service level bars. "
                            "forecast = forecasted demand line with trend. "
                            "revenue_at_risk = top at-risk revenue bars. "
                            "top_skus = top SKU revenue bars."
                        ),
                    },
                    "store": {
                        "type": "string",
                        "description": "Optional store filter. Only pass when the user asks about a specific store.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter. Only pass when the user asks about a specific "
                                       "category.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Limit result to top N items (default 8, max 20). Not used for trend/line "
                                       "charts.",
                    },
                },
                "required": ["chart_type", "data_scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_map",
            "description": (
                "Display an interactive map of Careem's dark-store locations across "
                "Dubai. Use this when the user asks to see stores on a map, "
                "delivery zones, store locations, or geographic distribution. "
                "The map will render below your text with interactive toggles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "view": {
                        "type": "string",
                        "enum": ["health", "revenue", "delivery"],
                        "description": (
                            "health = RAG-colored markers by scorecard health (green/amber/red). "
                            "revenue = markers colored by revenue contribution (dark green = biggest). "
                            "delivery = shows 30-min delivery zone circles around each store."
                        ),
                    },
                    "store": {
                        "type": "string",
                        "description": "Optional: zoom the map to a specific store. Only pass when the user asks "
                                       "about one store.",
                    },
                },
                "required": ["view"],
            },
        },
    },
]


def generate_plot(df, cat_perf, store_perf, top, forecast_dict, inv_summary,
                  revenue_risk, recent_demand, daily_revenue, inv,
                  chart_type, data_scope, store=None, category=None, top_n=8):
    """Generate an altair chart from analysis data. Returns (chart, summary_dict)."""
    GREEN = "#00E784"
    DARK = "#E8F4F8"
    MID = "#94B8C4"
    LIGHT = "#162E50"

    chart = None
    summary = {"chart_type": chart_type, "data_scope": data_scope}

    data = None
    x_col = ""
    y_col = ""
    color_col = ""

    # ── Select and prepare data ──
    if data_scope == "revenue_trend":
        data = daily_revenue.copy()
        x_col, y_col = "date", "revenue"
        chart_type = "line"
        summary["title"] = "Daily Revenue"
        summary["total"] = f"${data['revenue'].sum():,.0f}"

    elif data_scope == "demand_trend":
        data = recent_demand.copy()
        x_col, y_col = "date", "units_sold"
        chart_type = "line"
        summary["title"] = "Daily Demand (Units)"
        summary["total_units"] = f"{data['units_sold'].sum():,}"

        # Build forecast overlay data
        fc_rows = []
        if forecast_dict:
            last_date = df["date"].max()
            for st_name, fc_info in forecast_dict.items():
                if fc_info.get("forecast"):
                    for i, val in enumerate(fc_info["forecast"]):
                        fc_rows.append({
                            "date": last_date + pd.Timedelta(days=i + 1),
                            "units_sold": int(round(val)),
                            "store": st_name,
                        })
            fc_df = pd.DataFrame(fc_rows)
            if not fc_df.empty:
                # Compute historical avg for all stores
                hist_lines = []
                for st_name in df["store"].unique():
                    st_hist = df[df["store"] == st_name].groupby("date")["units_sold"].sum().reset_index()
                    st_hist["store"] = st_name
                    hist_lines.append(st_hist)
                hist_df = pd.concat(hist_lines, ignore_index=True)
                hist_df = hist_df.sort_values("date")

                hist_chart = (
                    alt.Chart(hist_df)
                    .mark_line(opacity=0.3, strokeWidth=1)
                    .encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("units_sold:Q", title="Units"),
                        color=alt.Color("store:N", legend=None),
                    )
                )
                fc_chart = (
                    alt.Chart(fc_df)
                    .mark_line(strokeDash=[4, 4], strokeWidth=2)
                    .encode(
                        x=alt.X("date:T"),
                        y=alt.Y("units_sold:Q"),
                        color=alt.Color("store:N", title="Store"),
                    )
                )
                chart = (hist_chart + fc_chart).properties(
                    title=alt.TitleParams("Daily Demand with 14-Day Forecast", color=DARK),
                    height=350,
                ).configure_axis(labelColor=MID, titleColor=MID)
                summary["description"] = "Daily demand trend with 14-day forecast per store (dashed lines)"
                return chart, summary

    elif data_scope == "revenue_by_category":
        data = cat_perf.copy()
        x_col, y_col = "category", "total_revenue"
        chart_type = "bar"
        summary["title"] = "Revenue by Category"

    elif data_scope == "revenue_by_store":
        data = store_perf.copy()
        x_col, y_col = "store", "total_revenue"
        chart_type = "bar"
        summary["title"] = "Revenue by Store"

    elif data_scope == "stockout_by_category":
        data = cat_perf.copy()
        x_col, y_col = "category", "stockout_rate"
        chart_type = "bar"
        summary["title"] = "Stockout Rate by Category"

    elif data_scope == "stockout_by_store":
        data = store_perf.copy()
        x_col, y_col = "store", "stockout_rate"
        chart_type = "bar"
        summary["title"] = "Stockout Rate by Store"

    elif data_scope == "service_level":
        data = inv_summary.copy()
        x_col, y_col = "category", "avg_service_level"
        chart_type = "bar"
        summary["title"] = "Service Level by Category"

    elif data_scope == "forecast":
        chart_type = "line"
        rows = []
        if forecast_dict:
            last_date = df["date"].max()
            for st_name, fc_info in forecast_dict.items():
                if store and st_name.lower() != store.lower():
                    continue
                if fc_info.get("forecast"):
                    for i, val in enumerate(fc_info["forecast"]):
                        rows.append({
                            "date": last_date + pd.Timedelta(days=i + 1),
                            "units_sold": int(round(val)),
                            "store": st_name,
                        })
            if rows:
                fc_df = pd.DataFrame(rows)
                data = fc_df
                x_col, y_col = "date", "units_sold"
                color_col = "store"
                summary["title"] = "14-Day Demand Forecast"
        if data is not None and data.empty:
            chart = None
            summary["error"] = "No forecast data"

    elif data_scope == "revenue_at_risk":
        if revenue_risk:
            risk_df = pd.DataFrame(revenue_risk)
            if store:
                risk_df = risk_df[risk_df["store"].str.lower() == store.lower()]
            if category:
                risk_df = risk_df[risk_df["category"].str.lower() == category.lower()]
            risk_df = risk_df.sort_values("revenue_at_risk", ascending=False).head(top_n)
            risk_df["label"] = risk_df["store"] + " / " + risk_df["sku"]
            data = risk_df
            x_col, y_col = "label", "revenue_at_risk"
            chart_type = "bar"
            summary["title"] = "Top Revenue at Risk"

    elif data_scope == "top_skus":
        if category:
            top_f = top[top["category"].str.lower() == category.lower()]
        else:
            top_f = top
        data = top_f.sort_values("total_revenue", ascending=False).head(top_n).copy()
        x_col, y_col = "sku", "total_revenue"
        chart_type = "bar"
        summary["title"] = "Top SKUs by Revenue"

    # ── Apply store/category filter for general charts ──
    if data is not None and not data.empty and chart is None:
        if store and "store" in data.columns:
            data = data[data["store"].str.lower() == store.lower()]
        if category and "category" in data.columns:
            data = data[data["category"].str.lower() == category.lower()]

        if data_scope == "revenue_trend":
            data = data.sort_values("date")
        elif data_scope == "demand_trend":
            data = data.sort_values("date")

        if x_col and y_col and not data.empty:
            # Build summary values
            if y_col in data.columns:
                if pd.api.types.is_numeric_dtype(data[y_col]):
                    vals = data[y_col]
                    summary["min"] = _fmt_num(vals.min())
                    summary["max"] = _fmt_num(vals.max())
                    summary["avg"] = _fmt_num(vals.mean())
                    if data_scope in ("revenue_by_category", "revenue_by_store", "top_skus", "revenue_at_risk"):
                        top_item = data.sort_values(y_col, ascending=False).iloc[0]
                        top_name = top_item.get(x_col, top_item.get("label", "N/A"))
                        summary["top_item"] = f"{top_name}: {_fmt_num(top_item[y_col])}"

            # Build chart
            if chart_type == "line":
                encoding = {
                    "x": alt.X(f"{x_col}:T", title=x_col.replace("_", " ").title())
                    if data_scope in ("revenue_trend", "demand_trend") else alt.X(f"{x_col}:N",
                                                                                  title=x_col.replace("_",
                                                                                                      " ").title()),
                    "y": alt.Y(f"{y_col}:Q", title=y_col.replace("_", " ").title()),
                }
                if color_col and color_col in data.columns:
                    encoding["color"] = alt.Color(f"{color_col}:N", title=color_col.title())
                chart = (
                    alt.Chart(data)
                    .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(filled=True, size=50))
                    .encode(**encoding)
                )
            elif chart_type == "bar":
                label_sort = "x" if data_scope not in ("revenue_trend", "demand_trend") else None
                # Fix: handle case where x_col might be "date" for bar
                encoding = {
                    "x": alt.X(f"{x_col}:N", sort="-y", title=x_col.replace("_", " ").title()),
                    "y": alt.Y(f"{y_col}:Q", title=y_col.replace("_", " ").title()),
                }
                color_enc = alt.Color(f"{x_col}:N", legend=None) if x_col == "category" or x_col == "store" \
                    else alt.value(GREEN)
                encoding["color"] = color_enc
                chart = (
                    alt.Chart(data)
                    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                    .encode(**encoding)
                )
            elif chart_type == "scatter":
                encoding = {
                    "x": alt.X(f"{x_col}:Q", title=x_col.replace("_", " ").title()),
                    "y": alt.Y(f"{y_col}:Q", title=y_col.replace("_", " ").title()),
                }
                if color_col and color_col in data.columns:
                    encoding["color"] = alt.Color(f"{color_col}:N")
                chart = alt.Chart(data).mark_point(filled=True, size=100).encode(**encoding)

            if chart:
                chart = chart.properties(
                    title=alt.TitleParams(
                        summary.get("title", ""),
                        subtitle=summary.get("top_item", ""),
                        color=DARK,
                    ),
                    height=350,
                ).configure_axis(
                    labelColor=MID, titleColor=MID, gridColor=LIGHT,
                ).configure_title(color=DARK).configure_view(strokeWidth=0)

    if chart is None:
        summary["error"] = f"No data available for {data_scope}"

    return chart, summary


def generate_map(df, store_perf, inv, scorecard, cat_perf, top,
                 view="health", store=None):
    """Generate an interactive folium map. Returns (folium_map, summary_dict)."""
    from analysis.mapping import build_store_map

    m = build_store_map(
        df=df,
        store_perf=store_perf,
        inv=inv,
        scorecard=scorecard,
        cat_perf=cat_perf,
        top=top,
        view=view,
        focus_store=store,
    )

    store_count = len(store_perf) if store_perf is not None else 0
    store_names = ", ".join(store_perf["store"].tolist()) if store_perf is not None and not store_perf.empty else "none"

    summary = {
        "title": f"Careem Grocery — {view.title()} View",
        "type": "interactive map",
        "stores": store_count,
        "store_names": store_names,
        "view": view,
        "description": (
            f"Map showing {store_count} dark stores in Dubai. "
            f"{'Colored by RAG health scores' if view == 'health' else ''}"
            f"{'Colored by revenue contribution' if view == 'revenue' else ''}"
            f"{'Showing 30-minute delivery zones' if view == 'delivery' else ''}"
            f". Click any store for detailed metrics. Use layer control to switch views."
        ),
    }
    if store:
        summary["focus"] = store

    return m, summary


def _fmt_num(v):
    """Format a number for summary output: 1234567 → $1.23M or 0.234 → 23.4%."""
    if v is None:
        return "N/A"
    if isinstance(v, float) and 0 <= v <= 1:
        return f"{v:.1%}"
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.1f}k"
    return f"${v:,.0f}"


INITIAL_BRIEFING_USER_MESSAGE = (
    "Give me your opening briefing, Careem. Channel your full personality. "
    "Start with the single most important number or risk — lead with it. "
    "Then 3-4 bullets with specific stores, SKUs, and figures. "
    "Close with one of your proverbs and a sign-off. "
    "This is my first time meeting you — make it memorable, Captain. "
    "7-10 sentences max."
)


def compute_careem_mood(anomalies, scorecard, inv, flags, tiered):
    """Return Careem's current mood with diagnosis and next-step suggestion."""
    mood = {
        "emoji": "😎",
        "label": "Chilling",
        "suggestion": "All metrics look healthy. Careem is ready for your questions.",
    }

    anomaly_rate = anomalies.get("anomaly_rate", 0) if anomalies else 0

    health_pct = 100
    if scorecard and scorecard.get("summary"):
        pcts = [
            d.get("health_pct", 100)
            for d in scorecard["summary"].values()
            if isinstance(d, dict)
        ]
        if pcts:
            health_pct = sum(pcts) / len(pcts)

    avg_service = 100
    if inv is not None and not (hasattr(inv, "empty") and inv.empty):
        if "service_level" in inv.columns:
            avg_service = inv["service_level"].mean()
        elif "avg_service_level" in inv.columns:
            avg_service = inv["avg_service_level"].mean()

    critical_flags = 0
    high_flags = 0
    total_flags = len(flags) if flags else 0
    if flags:
        for f in flags:
            severity = f.get("severity", f.get("risk", "")).lower()
            if "critical" in severity or "s1" in severity:
                critical_flags += 1
            elif "high" in severity or "s2" in severity:
                high_flags += 1

    s1_count = len(tiered.get("s1", [])) if tiered else 0

    if critical_flags >= 4 or anomaly_rate > 25:
        mood = {
            "emoji": "🤯",
            "label": "Can't unsee this",
            "suggestion": (
                f"{critical_flags} critical flags, {s1_count} S1 items, "
                f"{anomaly_rate}% anomaly days. "
                "Go to Inventory Health → filter S1 Critical Items. "
                "Then ask Careem: \"Run a full risk assessment.\""
            ),
        }
    elif critical_flags >= 2 or anomaly_rate > 20 or avg_service < 80:
        mood = {
            "emoji": "😤",
            "label": "Stressed",
            "suggestion": (
                f"{critical_flags} critical flags, service at {avg_service:.0f}%. "
                "Check Inventory Health for the S1 items table. "
                "Ask Careem: \"Which items should I address first?\""
            ),
        }
    elif high_flags >= 5 or anomaly_rate > 10 or health_pct < 50:
        mood = {
            "emoji": "😬",
            "label": "Concerned",
            "suggestion": (
                f"{high_flags} high-risk flags, health at {health_pct:.0f}%. "
                "Review the S&OP Scorecard for red items. "
                "Ask Careem: \"Show me the revenue-at-risk breakdown.\""
            ),
        }
    elif anomaly_rate > 5 or health_pct < 70 or avg_service < 95:
        mood = {
            "emoji": "😐",
            "label": "Cautious",
            "suggestion": (
                f"Health at {health_pct:.0f}%, {anomaly_rate}% anomaly days. "
                "Check the Forecast page for demand trends. "
                "Ask Careem: \"What should I keep an eye on?\""
            ),
        }
    elif health_pct < 85:
        mood = {
            "emoji": "🙂",
            "label": "Optimistic",
            "suggestion": (
                f"Health at {health_pct:.0f}% — solid but not perfect. "
                "A few items in amber. Ask Careem: \"Any early warnings?\""
            ),
        }

    mood["total_flags"] = total_flags
    mood["critical_flags"] = critical_flags
    mood["health_pct"] = health_pct
    mood["anomaly_rate"] = anomaly_rate
    return mood


def build_chat_context(stats, cat_perf, store_perf, top, inv_summary, flags,
                       forecast, anomalies, scorecard, tiered, revenue_risk,
                       cat_gaps, forec_conf):
    """Build a compact snapshot of the latest analysis for the chat LLM context."""
    lines = ["# Careem Grocery — Current State", "\n## Overview", f"- Revenue: ${stats['total_revenue']:,.0f}",
             f"- Units sold: {stats['total_units']:,}",
             f"- SKUs: {stats['num_skus']} across {stats['num_categories']} categories",
             f"- Stores: {stats['num_stores']}", f"- Avg order value: ${stats['avg_order_value']:.2f}",
             f"- Period: {stats['date_range']}", "\n## Category Performance"]

    for _, r in cat_perf.iterrows():
        lines.append(
            f"- **{r['category']}**: ${r['total_revenue']:,.0f} "
            f"({r['revenue_share']:.0f}% share), "
            f"{r['stockout_rate']:.1%} stockout, "
            f"{r['promo_frequency']:.1%} promo rate"
        )

    lines.append("\n## Store Performance")
    for _, r in store_perf.iterrows():
        lines.append(
            f"- **{r['store']}**: ${r['total_revenue']:,.0f} "
            f"({r['revenue_share']:.0f}% share), "
            f"{r['stockout_rate']:.1%} stockout"
        )

    lines.append("\n## Top 5 SKUs by Revenue")
    for _, r in top.head(5).iterrows():
        lines.append(
            f"- **{r['sku']}** ({r['category']}): "
            f"${r['total_revenue']:,.0f}, "
            f"{r['total_units']:,.0f} units, "
            f"{r['stockout_rate']:.1%} stockout"
        )

    lines.append("\n## Inventory Health by Category")
    for _, r in inv_summary.iterrows():
        lines.append(
            f"- **{r['category']}**: {r['avg_service_level']:.1f}% service, "
            f"{r['total_stockout_days']} stockout days, "
            f"${r['total_revenue_at_risk']:,.0f} revenue at risk, "
            f"{r['skus_at_risk']} SKUs below 95%"
        )

    lines.append("\n## 14-Day Forecast (units)")
    for store, data in forecast.items():
        lines.append(f"- **{store}**: {data['next_14d_total']:,}")

    if flags:
        lines.append(f"\n## Risk Flags (top 10 of {len(flags)} total)")
        for f in flags[:10]:
            lines.append(
                f"- **{f['store']} / {f['sku']}** ({f['category']}): "
                f"{f['risk']} — {f['detail']} ({f['metric']})"
            )

    if anomalies and not anomalies.get("empty", True):
        rate = anomalies.get("anomaly_rate", 0)
        lines.append(f"\n## Anomalies ({rate}% of days flagged)")
        for a in anomalies.get("top_anomalies", [])[:3]:
            date_str = a.get("date", "")
            desc = a.get("description", "")
            lines.append(f"- {date_str}: {desc}")

    if scorecard and scorecard.get("summary"):
        lines.append("\n## S&OP Scorecard")
        for store, data in scorecard["summary"].items():
            lines.append(
                f"- **{store}**: {data.get('health_pct', 0):.0f}% healthy "
                f"({data.get('green', 0)}G / {data.get('amber', 0)}A / {data.get('red', 0)}R)"
            )

    if revenue_risk:
        total_risk = sum(r.get("revenue_at_risk", 0) for r in revenue_risk)
        lines.append(f"\n## Revenue at Risk: ${total_risk:,.0f} (top items)")
        for r in revenue_risk[:5]:
            lines.append(
                f"- **{r['store']} / {r['sku']}**: "
                f"${r.get('revenue_at_risk', 0):,.0f} at risk, "
                f"{r.get('stockout_days', 0)} stockout days"
            )

    if cat_gaps:
        lines.append("\n## Store × Category Gaps")
        for g in cat_gaps.get("top_underperformers", [])[:3]:
            lines.append(f"- Weak: **{g['store']} / {g['category']}** ({g['gap']}) — {g['detail']}")
        for g in cat_gaps.get("top_overperformers", [])[:3]:
            lines.append(f"- Strong: **{g['store']} / {g['category']}** ({g['gap']}) — {g['detail']}")

    if tiered and tiered.get("s1"):
        lines.append("\n## S1 Critical Items")
        for r in tiered["s1"][:5]:
            lines.append(
                f"- **{r['store']} / {r['sku']}** ({r['category']}): "
                f"{r.get('revenue_at_risk', 'N/A')} at risk, "
                f"{r.get('stockout_days', '?')} stockout days, "
                f"{r.get('service_level', '?')} service"
            )

    if forec_conf:
        lines.append("\n## Forecast Confidence")
        for item in forec_conf:
            lines.append(
                f"- **{item['store']}**: {item.get('confidence', '?')} "
                f"(volatility: {item.get('daily_volatility', '?')}, "
                f"range: {item.get('range_14d', '?')})"
            )

    return "\n".join(lines)


def call_chat_api(api_key, api_base, model, messages, tools=None, execute_tool=None, timeout=120):
    """Send chat messages to the LLM. Handles tool calls if tools/execute_tool provided.

    Returns (text_response: str, artifacts: list).
    artifacts may contain altair charts to be displayed alongside the response.
    """
    base = (api_base or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"

    payload = {
        "model": model or "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2500,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )

    if response.is_error:
        raise Exception(f"API returned {response.status_code}: {response.text[:500]}")

    result = response.json()
    choice = result["choices"][0]
    msg = choice["message"]
    artifacts = []

    # Handle tool calls
    if choice.get("finish_reason") == "tool_calls" or msg.get("tool_calls"):
        tool_calls = msg["tool_calls"] or []
        tool_results = []

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}

            if execute_tool and fn_name in execute_tool:
                chart, summary = execute_tool[fn_name](**fn_args)
                if chart is not None:
                    artifacts.append(chart)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(summary, default=str),
                })
            else:
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps({"error": f"Unknown tool: {fn_name}"}),
                })

        # Append assistant tool-calls message + tool results to a copy of messages
        follow_up_msgs = list(messages) + [msg] + tool_results

        payload2 = {
            "model": model or "gpt-4o-mini",
            "messages": follow_up_msgs,
            "temperature": 0.3,
            "max_tokens": 2500,
        }

        resp2 = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload2,
            timeout=timeout,
        )

        if resp2.is_error:
            raise Exception(f"API returned {resp2.status_code} on tool follow-up: {resp2.text[:500]}")

        final_text = resp2.json()["choices"][0]["message"]["content"]
        return final_text, artifacts

    return msg["content"] or "", artifacts
