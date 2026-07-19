import altair as alt
import pandas as pd


def revenue_category_chart(cat_df):
    return (
        alt.Chart(cat_df)
        .mark_bar()
        .encode(
            x=alt.X("category:N", title=None),
            y=alt.Y("total_revenue:Q", title="Revenue ($)"),
            color=alt.Color("category:N", legend=None),
            tooltip=["category", "total_revenue"],
        )
        .properties(height=300)
    )


def revenue_store_chart(store_df):
    return (
        alt.Chart(store_df)
        .mark_bar()
        .encode(
            x=alt.X("store:N", title=None),
            y=alt.Y("total_revenue:Q", title="Revenue ($)"),
            color=alt.Color("store:N", legend=None),
            tooltip=["store", "total_revenue"],
        )
        .properties(height=300)
    )


def weekday_pattern_chart(weekday_df):
    return (
        alt.Chart(weekday_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("day:N", title=None, sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
            y=alt.Y("avg_units:Q", title="Avg units sold"),
            color=alt.value("#00E784"),
        )
        .properties(height=250)
    )


def promo_impact_chart(promo_df):
    promo_df = promo_df.copy()
    promo_df["promotion"] = promo_df["promotion"].map({True: "Promo", False: "Regular"})

    return (
        alt.Chart(promo_df)
        .mark_bar()
        .encode(
            x=alt.X("promotion:N", title=None),
            y=alt.Y("avg_units_sold:Q", title="Avg units sold"),
            color=alt.Color("promotion:N", legend=None),
            tooltip=["promotion", "avg_units_sold"],
        )
        .properties(height=250)
    )


def daily_demand_chart(df, date_col="date", date_max=None):
    if date_max is None:
        date_max = df[date_col].max()

    recent = df[df[date_col] >= date_max - pd.Timedelta(days=30)]

    daily = (
        recent.groupby(date_col)
        .agg(units_sold=("units_sold", "sum"))
        .reset_index()
        .sort_values(date_col)
    )

    return (
        alt.Chart(daily)
        .mark_line()
        .encode(
            x=alt.X(f"{date_col}:T", title=None),
            y=alt.Y("units_sold:Q", title="Units sold"),
        )
        .properties(height=300)
    )


def service_level_chart(inv_summary):
    return (
        alt.Chart(inv_summary)
        .mark_bar()
        .encode(
            x=alt.X("category:N", title=None),
            y=alt.Y("avg_service_level:Q", title="Service level (%)"),
            color=alt.Color("category:N", legend=None),
            tooltip=["category", "avg_service_level"],
        )
        .properties(height=250)
    )


def stockout_chart(inv_summary):
    return (
        alt.Chart(inv_summary)
        .mark_bar()
        .encode(
            x=alt.X("category:N", title=None),
            y=alt.Y("total_stockout_days:Q", title="Stockout days"),
            color=alt.Color("category:N", legend=None),
            tooltip=["category", "total_stockout_days"],
        )
        .properties(height=250)
    )


def forecast_chart(hist_df, forecast_df, store_label):
    hist = hist_df.copy()
    hist["type"] = "Historical"

    fcast = forecast_df.copy()
    fcast["type"] = "Forecast"

    color_scale = alt.Scale(
        domain=["Historical", "Forecast"],
        range=["#00E784", "#A6EDF2"],
    )

    hist_line = (
        alt.Chart(hist)
        .mark_line(point=False)
        .encode(
            x=alt.X("date:T"),
            y=alt.Y("units_sold:Q"),
            color=alt.Color("type:N", scale=color_scale, legend=alt.Legend(title=None)),
        )
    )

    fcast_line = (
        alt.Chart(fcast)
        .mark_line(strokeDash=[8, 4], point=False)
        .encode(
            x=alt.X("date:T"),
            y=alt.Y("units_sold:Q"),
            color=alt.Color("type:N", scale=color_scale, legend=alt.Legend(title=None)),
        )
    )

    return (
        alt.layer(hist_line, fcast_line)
        .properties(title=f"14-day demand forecast — {store_label}", height=400)
        .encode(x=alt.X("date:T", title="Date"), y=alt.Y("units_sold:Q", title="Units sold"))
    )
