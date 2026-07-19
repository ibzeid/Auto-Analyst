"""Interactive store map for Careem Grocery's dark-store network in Dubai."""

import folium
from folium import FeatureGroup, LayerControl


STORE_COORDS = {
    "Downtown Hub": (25.1972, 55.2744),
    "Marina Express": (25.0804, 55.1401),
    "JLT QuickStop": (25.0699, 55.1414),
    "Palm Satellite": (25.1124, 55.1390),
    "Deira Depot": (25.2658, 55.3185),
}

DELIVERY_RADIUS_M = 7_000


def _rag_color(health_pct):
    if health_pct >= 85:
        return "#00E784"
    elif health_pct >= 60:
        return "#FFC107"
    return "#FF5252"


def _revenue_color(revenue_share):
    if revenue_share >= 25:
        return "#00493E"
    elif revenue_share >= 18:
        return "#006B5A"
    elif revenue_share >= 12:
        return "#00B865"
    return "#00E784"


def _popup_html(store_name, store_row, inv, scorecard, df):
    """Build rich HTML popup for a store marker."""
    rev = store_row.get("total_revenue", 0)
    share = store_row.get("revenue_share", 0)
    stockout = store_row.get("stockout_rate", 0)

    health = 100
    if scorecard and scorecard.get("summary") and store_name in scorecard["summary"]:
        health = scorecard["summary"][store_name].get("health_pct", 100)

    svc_level = 100
    store_inv = inv[inv["store"] == store_name] if "store" in inv.columns else inv
    if not store_inv.empty and "service_level" in store_inv.columns:
        svc_level = store_inv["service_level"].mean() * 100

    top_skus_html = ""
    store_df = df[df["store"] == store_name] if df is not None else None
    if store_df is not None and not store_df.empty:
        sku_rev = store_df.groupby("sku")["revenue"].sum().nlargest(3)
        top_skus_html = '<div style="margin-top:6px;font-size:11px;color:#00493E;">'
        for sku, r in sku_rev.items():
            top_skus_html += f"&bull; {sku} &mdash; ${r:,.0f}<br>"
        top_skus_html += "</div>"

    rag_c = _rag_color(health)
    return f"""
    <div style="font-family:sans-serif;min-width:200px;">
      <h4 style="margin:0 0 6px;color:#00493E;">{store_name}</h4>
      <div style="font-size:13px;color:#00493E;">
        <b>Revenue:</b> ${rev:,.0f} &nbsp;({share:.0f}% of total)<br>
        <b>Stockout rate:</b> {stockout:.1%}<br>
        <b>Service level:</b> {svc_level:.1f}%<br>
        <b>Health:</b> <span style="color:{rag_c};font-weight:700;">{health:.0f}%</span>
      </div>
      {top_skus_html}
    </div>
    """


def _tooltip_html(store_name, store_row):
    rev = store_row.get("total_revenue", 0)
    stockout = store_row.get("stockout_rate", 0)
    return (
        f"<b>{store_name}</b><br>"
        f"${rev:,.0f} revenue<br>"
        f"{stockout:.1%} stockout"
    )


def build_store_map(df, store_perf, inv, scorecard, cat_perf, top,
                    view="health", focus_store=None):
    """Build an interactive folium map of Careem's dark-store network.

    Store markers are always visible. Coloring follows the selected ``view``
    (RAG health, revenue gradient, or green delivery).  The 30‑min delivery
    zones are a toggleable overlay.

    Args:
        view: 'health' (RAG colors), 'revenue' (revenue-graded), 'delivery'
        focus_store: optional store name to zoom to
    """
    center = (25.13, 55.20)
    zoom = 11
    if focus_store and focus_store in STORE_COORDS:
        center = STORE_COORDS[focus_store]
        zoom = 13

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    delivery_zone_group = FeatureGroup(name="Delivery Zones (30 min)", show=True)

    for store_name, (lat, lon) in STORE_COORDS.items():
        s_row = store_perf[store_perf["store"] == store_name]
        if s_row.empty:
            continue
        s_row = s_row.iloc[0]
        share = s_row.get("revenue_share", 0)

        avg_health = 100
        if scorecard and scorecard.get("summary") and store_name in scorecard["summary"]:
            avg_health = scorecard["summary"][store_name].get("health_pct", 100)

        popup = folium.Popup(
            _popup_html(store_name, s_row, inv, scorecard, df),
            max_width=300,
        )
        tooltip = folium.Tooltip(_tooltip_html(store_name, s_row))

        # Colour the circle marker based on the active view
        if view == "revenue":
            circle_color = _revenue_color(share)
        elif view == "delivery":
            circle_color = "#00E784"
        else:  # health
            circle_color = _rag_color(avg_health)

        marker_radius = max(8, int(14 + share / 3))

        folium.CircleMarker(
            location=(lat, lon),
            radius=marker_radius,
            color="#001942",
            weight=2,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.85,
            popup=popup,
            tooltip=tooltip,
        ).add_to(m)

        # Store label floating beside the marker
        label_html = (
            f'<div style="font-size:12px;font-weight:700;color:#001942;'
            f'background:rgba(255,255,255,0.92);padding:2px 8px;'
            f'border-radius:5px;white-space:nowrap;'
            f'border:2px solid {circle_color};'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.12);">'
            f'{store_name}</div>'
        )
        folium.Marker(
            location=(lat, lon),
            icon=folium.DivIcon(
                html=label_html,
                icon_size=(150, 28),
                icon_anchor=(75, 22),
            ),
        ).add_to(m)

        # Delivery zone (toggleable overlay)
        folium.Circle(
            location=(lat, lon),
            radius=DELIVERY_RADIUS_M,
            color="#00E784",
            weight=1.5,
            fill=True,
            fill_color="#00E784",
            fill_opacity=0.06,
            dash_array="6, 6",
            popup=folium.Popup(
                f"<b>{store_name}</b><br>30-min delivery zone (~7 km)",
                max_width=220,
            ),
        ).add_to(delivery_zone_group)

    delivery_zone_group.add_to(m)

    if not focus_store:
        m.fit_bounds(
            [[c[0] - 0.025, c[1] - 0.025] for c in STORE_COORDS.values()]
            + [[c[0] + 0.025, c[1] + 0.025] for c in STORE_COORDS.values()],
            max_zoom=12,
        )

    LayerControl(collapsed=False).add_to(m)
    return m
