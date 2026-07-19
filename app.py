import base64

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from functools import partial
import altair as alt

from data.generate_data import generate_data
from analysis.stats import (
    summary_stats, category_performance, store_performance, top_skus,
    promo_impact, weekday_pattern, revenue_at_risk, store_category_gaps,
)
from analysis.forecast import forecast_all_stores, forecast_confidence_summary
from analysis.inventory import inventory_health, risk_flags, category_inventory_summary, tiered_risks
from analysis.scorecard import rag_scorecard
from analysis.scenario import run_scenario
from analysis.anomaly import detect_anomalies
from insights.chat import (
    build_chat_context, call_chat_api,
    INITIAL_BRIEFING_USER_MESSAGE, compute_careem_mood,
    TOOLS, generate_plot, generate_map,
)
from insights.agents import AGENTS, parse_mention, detect_consult

import folium

st.set_page_config(
    page_title="Auto-Analyst — Careem Grocery",
    page_icon=":material/analytics:",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background: #001942; }

    .block-container {
        padding-top: 2.5rem !important;
    }

    [data-testid="stMetric"] {
        background: #0A2A52;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
        padding: 0.75rem 1rem !important;
        transition: box-shadow 0.2s ease, transform 0.2s ease;
        border: 1px solid rgba(0, 231, 132, 0.12);
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 18px rgba(0, 231, 132, 0.12);
        transform: translateY(-1px);
    }
    [data-testid="stMetric"] label {
        color: #94B8C4 !important;
        font-size: 0.8rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 2px solid rgba(0, 231, 132, 0.20);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
        color: #94B8C4;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(0, 231, 132, 0.10);
        color: #FFFFFF;
    }
    .stTabs [aria-selected="true"] {
        background: #00E784 !important;
        color: #001942 !important;
    }

    .stSidebar {
        background: #000E24 !important;
    }
    .stSidebar * {
        color: #94B8C4 !important;
    }
    .stSidebar h4, .stSidebar h5 { color: #00E784 !important; }
    .stSidebar .stButton button {
        background: #00E784 !important;
        color: #001942 !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
    }
    .stSidebar .stButton button:hover {
        opacity: 0.88;
        box-shadow: 0 4px 24px rgba(0, 231, 132, 0.30);
    }
    .stSidebar .stButton button:disabled {
        background: #1A3358 !important;
        color: #6B7D99 !important;
        box-shadow: none !important;
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }
    }

    .chat-card {
        border: 2px solid rgba(0, 231, 132, 0.18) !important;
        border-radius: 16px !important;
        background: #0A2A52 !important;
        box-shadow: 0 2px 16px rgba(0, 0, 0, 0.20) !important;
    }
    .chat-card > div:first-child {
        padding: 1.5rem !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid rgba(0, 231, 132, 0.15) !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18) !important;
        background: #0A2A52 !important;
    }

    [data-testid="stChatMessage"] {
        word-break: normal !important;
        overflow-wrap: normal !important;
    }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {
        word-break: normal !important;
        overflow-wrap: normal !important;
    }

    /* Careem avatar glow */
    [data-testid="stChatMessage"] img[alt="assistant"] {
        border: 2px solid #00E784 !important;
        border-radius: 50% !important;
        box-shadow: 0 0 0 3px rgba(0, 231, 132, 0.25) !important;
    }

    .sidebar-header {
        text-align: center;
        padding: 0.5rem 0.25rem 0.75rem;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid rgba(0, 231, 132, 0.15);
    }
    .sidebar-logo {
        height: 58px;
        width: auto;
        margin-bottom: 0.5rem;
    }
    .sidebar-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #00E784;
        margin: 0 0 0.15rem;
    }
    .sidebar-subtitle {
        font-size: 0.7rem;
        color: #94B8C4;
        margin: 0;
        line-height: 1.3;
    }
</style>
""", unsafe_allow_html=True)

SAMPLE_DATA_PATH = "data/sample_grocery_data.csv"


@st.cache_data
def load_sample_data():
    if not os.path.exists(SAMPLE_DATA_PATH):
        df_ = generate_data()
        os.makedirs("data", exist_ok=True)
        df_.to_csv(SAMPLE_DATA_PATH, index=False)
        return df_
    return pd.read_csv(SAMPLE_DATA_PATH, parse_dates=["date"])


def run_analysis(df_):
    stats_ = summary_stats(df_)
    cat_perf_ = category_performance(df_)
    store_perf_ = store_performance(df_)
    top_ = top_skus(df_)
    promo_, lift_ = promo_impact(df_)
    weekday_ = weekday_pattern(df_)
    inv_ = inventory_health(df_)
    flags_ = risk_flags(inv_)
    inv_summary_ = category_inventory_summary(inv_)
    forecast_ = forecast_all_stores(df_)
    revenue_risk_ = revenue_at_risk(inv_)
    cat_gaps_ = store_category_gaps(df_)
    forec_conf_ = forecast_confidence_summary(forecast_)
    tiered_ = tiered_risks(inv_)
    scorecard_ = rag_scorecard(inv_, cat_perf_, store_perf_)
    anomalies_ = detect_anomalies(df_)
    return (stats_, cat_perf_, store_perf_, top_, promo_, lift_, weekday_,
            inv_, flags_, inv_summary_, forecast_,
            revenue_risk_, cat_gaps_, forec_conf_, tiered_, scorecard_, anomalies_)


_logo_path = os.path.join(os.path.dirname(__file__), "assets", "careem-logo-white.svg")
_logo_b64 = ""
if os.path.exists(_logo_path):
    with open(_logo_path, "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()

with st.sidebar:
    if _logo_b64:
        st.markdown(
            f'<div class="sidebar-header">'
            f'<img class="sidebar-logo" src="data:image/svg+xml;base64,{_logo_b64}" alt="Careem" />'
            f'<p class="sidebar-title">Auto-Analyst</p>'
            f'<p class="sidebar-subtitle">Demand planning dashboard<br>for Careem Grocery</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### :material/dataset: Data source")
    data_option = st.radio(
        "Choose data",
        ["Use sample data", "Upload CSV"],
        index=0,
        label_visibility="collapsed",
    )

    df = None
    if data_option == "Upload CSV":
        uploaded = st.file_uploader("Upload grocery demand CSV", type=["csv"], label_visibility="collapsed")
        if uploaded:
            df = pd.read_csv(uploaded)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
    else:
        df = load_sample_data()

    st.divider()
    st.markdown("#### :material/psychology: AI insights")

    PROVIDERS = {
        "OpenAI": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "key_hint": "sk-..."},
        "DeepSeek": {"base_url": "https://api.deepseek.com", "model": "deepseek-v4-flash", "key_hint": "sk-..."},
        "Anthropic (via OpenRouter)": {"base_url": "https://openrouter.ai/api/v1", "model": "anthropic/claude-sonnet-4",
                                       "key_hint": "sk-or-..."},
        "OpenRouter": {"base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini",
                       "key_hint": "sk-or-..."},
        "Groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile",
                 "key_hint": "gsk_..."},
        "Together": {"base_url": "https://api.together.xyz/v1", "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                     "key_hint": "tpi_..."},
        "Custom": {"base_url": "", "model": "", "key_hint": "API key"},
    }

    secret_key = secret_base = secret_model = ""
    try:
        secret_key = st.secrets.get("LLM_API_KEY", "")
        secret_base = st.secrets.get("LLM_API_BASE", "")
        secret_model = st.secrets.get("LLM_MODEL", "")
    except (FileNotFoundError, KeyError):
        pass

    env_key = os.environ.get("LLM_API_KEY", "")
    env_base = os.environ.get("LLM_API_BASE", "")
    env_model = os.environ.get("LLM_MODEL", "")

    resolved_key = secret_key or env_key
    resolved_base = secret_base or env_base
    resolved_model = secret_model or env_model

    if resolved_key:
        source = "secrets" if secret_key else "env var"
        st.info(f"Key loaded from `{source}`", icon=":material/lock:")
        api_key = resolved_key
        api_base = resolved_base
        model = resolved_model
    else:
        st.caption("Key not stored — enter below (or add to `.streamlit/secrets.toml`)")

        provider = st.selectbox(
            "Provider",
            options=list(PROVIDERS.keys()),
            index=0,
            label_visibility="collapsed",
            key="provider",
        )

        cfg = PROVIDERS[provider]

        api_key = st.text_input(
            "API key",
            type="password",
            placeholder=cfg["key_hint"],
            label_visibility="collapsed",
            help="Your API key for the selected provider.",
        )

        api_base = st.text_input(
            "API base URL",
            value=cfg["base_url"],
            placeholder="https://api.openai.com/v1",
            label_visibility="collapsed",
            help="Auto-filled from provider. Override if needed.",
        )

        model = st.text_input(
            "Model",
            value=cfg["model"],
            placeholder="gpt-4o-mini",
            label_visibility="collapsed",
            help="Auto-filled from provider. Override if needed.",
        )

    st.divider()
    st.markdown("#### :material/folder: Data explorer")
    explorer_page = st.radio(
        "Sections",
        ["Overview", "Talk to Careem", "Store Map", "Category & stores", "Demand patterns",
         "Inventory health", "Forecast", "S&OP Scorecard"],
        label_visibility="collapsed",
        index=0,
    )
    st.divider()
    boardroom = st.toggle("Boardroom mode", help="Clean, presentation-ready view")
    st.caption("Built for the Careem challenge")

if df is None:
    st.info("Upload a CSV or use sample data to get started.", icon=":material/upload_file:")
    st.stop()

with st.spinner("Analyzing demand data..."):
    results = run_analysis(df)
    stats, cat_perf, store_perf, top, promo, lift, weekday, inv, flags, inv_summary, forecast, revenue_risk, cat_gaps, forec_conf, tiered, scorecard, anomalies = results

recent_demand = (
    df[df["date"] >= df["date"].max() - pd.Timedelta(days=28)]
    .groupby("date")["units_sold"].sum()
    .reset_index()
    .sort_values("date")
)
daily_revenue = (
    df[df["date"] >= df["date"].max() - pd.Timedelta(days=28)]
    .groupby("date")["revenue"].sum()
    .reset_index()
    .sort_values("date")
)
stockout_rate = round(inv["stockout_days"].sum() / inv["total_days"].sum() * 100, 1)
forecast_total = sum(d["next_14d_total"] for d in forecast.values())

# ── Session state ──
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_initialized" not in st.session_state:
    st.session_state.chat_initialized = False
if "active_agent" not in st.session_state:
    st.session_state.active_agent = "careem"


def _chat_ctx():
    return build_chat_context(
        stats, cat_perf, store_perf, top, inv_summary, flags,
        forecast, anomalies, scorecard, tiered, revenue_risk, cat_gaps, forec_conf,
    )


_plot_fn = partial(
    generate_plot,
    df, cat_perf, store_perf, top, forecast, inv_summary,
    revenue_risk, recent_demand, daily_revenue, inv,
)

_map_fn = partial(
    generate_map,
    df, store_perf, inv, scorecard, cat_perf, top,
)


def _render_artifact(artifact):
    """Render a chat artifact (altair chart or folium map)."""
    if isinstance(artifact, folium.Map):
        html_str = getattr(artifact, "_repr_html_")()
        components.html(html_str, height=480, scrolling=False)
    else:
        st.altair_chart(artifact, width="stretch")


# ── Boardroom mode ──
if boardroom:
    st.markdown("## S&OP Decision Brief — Boardroom View")
    if st.session_state.chat_messages:
        st.markdown("---")
        for msg in st.session_state.chat_messages:
            if msg["role"] == "assistant":
                agent_cfg = AGENTS.get(msg.get("agent", "careem"), AGENTS["careem"])
                st.markdown(
                    f"### <img src='{agent_cfg['avatar']}' "
                    f"style='width:28px;height:28px;border-radius:50%;vertical-align:middle;margin-right:6px;' /> "
                    f"{agent_cfg['name']} — {agent_cfg['role']}"
                )
            else:
                st.markdown("### :material/person: You")
            st.markdown(msg["content"])
            for artifact in msg.get("_charts", []):
                _render_artifact(artifact)
            st.markdown("---")
        st.caption("Generated by Careem Auto-Analyst | For internal S&OP review")
    else:
        st.info("Start a conversation in the chat to populate the boardroom view.", icon=":material/description:")
    st.stop()


# ── Content ──
def _display_mood_meter():
    mood = compute_careem_mood(anomalies, scorecard, inv, flags, tiered)
    mood_bg = {
        "😎": "#D6FFEA", "🙂": "#E8F8EE", "😐": "#FFF3CD",
        "😬": "#FFE0B2", "😤": "#FFCDD2", "🤯": "#F8D7DA",
    }
    suggestion = mood.get("suggestion", "")
    bg = mood_bg.get(mood["emoji"], "#D6FFEA")
    st.markdown(
        f'<div style="background:{bg};border-radius:8px;padding:0.5rem 1rem;margin-bottom:0.5rem;'
        f'color:#001942;">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;font-size:0.95rem;">'
        f'<span style="font-size:1.4rem;">{mood["emoji"]}</span>'
        f'<span><strong>{mood["label"]}</strong></span>'
        f'</div>'
        f'<div style="font-size:0.82rem;margin-top:0.2rem;line-height:1.45;'
        f'padding-left:2.2rem;">{suggestion}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _run_agent_turn(agent_key, user_prompt, extra_context=None):
    """Run one agent turn. Returns (response_text, charts, consulted_agent)."""
    agent_cfg = AGENTS[agent_key]
    ctx = _chat_ctx()

    api_messages = [{"role": "system", "content": agent_cfg["prompt"] + "\n\n" + ctx}]

    if extra_context:
        api_messages.append({"role": "user", "content": extra_context})

    api_messages.append({"role": "user", "content": user_prompt})

    response, charts = call_chat_api(
        api_key, api_base, model, api_messages,
        tools=TOOLS, execute_tool={"generate_plot": _plot_fn, "show_map": _map_fn},
    )

    consult_key, clean_response = detect_consult(response)
    return clean_response, charts, consult_key


# ═══════════════════════════════════════════════════════════════════════════
if explorer_page == "Overview":
    if anomalies and anomalies.get("recent_flag"):
        st.warning(
            f":material/warning: **Anomaly detected** — {anomalies['anomaly_rate']}% of days show unusual demand. "
            f"Latest: {anomalies['top_anomalies'][0]['description']}",
            icon=":material/warning:",
        )

    st.markdown(
        '<div style="background: linear-gradient(135deg, #0A2A52 0%, #0F3460 100%);'
        'border-left: 3px solid #00E784; border-radius: 10px; padding: 1rem 1.25rem;'
        'margin-bottom: 1rem; color: #E8F4F8; font-size: 0.88rem; line-height: 1.6;">'
        '<span style="color: #00E784; font-weight: 700; font-size: 0.8rem; '
        'text-transform: uppercase; letter-spacing: 0.05em;">Auto-Analyst</span>'
        '<p style="margin: 0.35rem 0 0;">'
        'An AI-powered demand planning dashboard for Careem Grocery that simulates a '
        'multi-agent executive <b style="color:#00E784;">War Room</b>. Three AI personas &mdash; '
        '<b style="color:#00E784;">Careem</b> (S&OP), <b style="color:#F5A623;">Rashid</b> (CFO), '
        'and <b style="color:#3B82F6;">Noor</b> (Ops) &mdash; analyze live supply chain data '
        'with Emirati voices and region-inspired proverbs. The platform generates charts and '
        'interactive Dubai store maps on command, detects anomalies, runs scenario simulations, '
        'and presents RAG scorecards. Agents autonomously consult each other, mirroring how a '
        'real S&OP team operates.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    _display_mood_meter()

    with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Revenue", f"${stats['total_revenue']:,.0f}", border=False)
        with m2:
            st.metric("Units (28d)", f"{recent_demand['units_sold'].sum():,.0f}", border=False)
        with m3:
            st.metric("Stockout rate", f"{stockout_rate}%", border=False)
        with m4:
            st.metric("Forecast (14d)", f"{forecast_total:,}", border=False)

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Demand (28 days)")
            demand_chart = (
                alt.Chart(recent_demand)
                .mark_line(strokeWidth=2, color="#00E784")
                .encode(
                    x=alt.X("date:T", title=None, axis=alt.Axis(labels=False)),
                    y=alt.Y("units_sold:Q", title=None),
                )
                .properties(height=200)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(demand_chart, width="stretch")

    with col2:
        with st.container(border=True):
            st.subheader("Revenue by category")
            cat_chart = (
                alt.Chart(cat_perf.nlargest(5, "total_revenue"))
                .mark_bar(color="#00E784")
                .encode(
                    x=alt.X("total_revenue:Q", title=None),
                    y=alt.Y("category:N", sort="-x", title=None),
                )
                .properties(height=200)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(cat_chart, width="stretch")


# ═══════════════════════════════════════════════════════════════════════════
elif explorer_page == "Talk to Careem":
    st.session_state.active_agent_key = st.session_state.get("active_agent_key", "careem")

    if anomalies and anomalies.get("recent_flag"):
        st.warning(
            f":material/warning: **Anomaly detected** — {anomalies['anomaly_rate']}% of days show unusual demand. "
            f"Latest: {anomalies['top_anomalies'][0]['description']}",
            icon=":material/warning:",
        )

    # ── Agent cards ──
    card_cols = st.columns(3)
    for i, (key, cfg) in enumerate(AGENTS.items()):
        with card_cols[i]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center;'>"
                    f"<img src='{cfg['avatar']}' "
                    f"style='width:44px;height:44px;border-radius:50%;border:2.5px solid {cfg['border']};' />"
                    f"<p style='margin:0.35rem 0 0;font-size:1rem;font-weight:700;color:#FFFFFF;'>{cfg['name']}</p>"
                    f"<p style='margin:0 0 0.4rem;font-size:0.75rem;color:{cfg['color']};font-weight:600;'>{cfg['role']}</p>"
                    f"<p style='margin:0;font-size:0.78rem;color:#94B8C4;line-height:1.4;'>{cfg['scope']}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Agent selector ──
    agent_key = st.pills(
        "Talk to...",
        options=["Careem", "Rashid", "Noor"],
        default="Careem",
        label_visibility="collapsed",
        key="agent_selector",
    )
    agent_map = {"Careem": "careem", "Rashid": "rashid", "Noor": "noor"}
    active_key = agent_map[agent_key]
    st.session_state.active_agent_key = active_key
    active_cfg = AGENTS[active_key]

    # ── Chat ──
    with st.container(border=True):
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;'>"
            f"<img src='{active_cfg['avatar']}' "
            f"style='width:34px;height:34px;border-radius:50%;' /> "
            f"{active_cfg['name']} — {active_cfg['role']}</h3>",
            unsafe_allow_html=True,
        )
        st.caption(active_cfg["scope"])

        # Initial briefing (Careem only)
        if api_key and not st.session_state.chat_initialized:
            with st.spinner("Careem is waking up and checking the numbers..."):
                try:
                    response, charts, _ = _run_agent_turn(
                        "careem", INITIAL_BRIEFING_USER_MESSAGE,
                    )
                    st.session_state.chat_messages.append({
                        "role": "assistant", "agent": "careem",
                        "content": response, "_charts": charts,
                    })
                except Exception as e:
                    st.error(f"Failed to generate briefing: {e}")
                finally:
                    st.session_state.chat_initialized = True

        for msg in st.session_state.chat_messages:
            role = msg["role"]
            agent_cfg = AGENTS.get(msg.get("agent", "careem"), AGENTS["careem"])
            avatar = agent_cfg["avatar"] if role == "assistant" else None

            with st.chat_message(role, avatar=avatar):
                if role == "assistant":
                    st.markdown(
                        f"<span style='font-size:0.8rem;color:{agent_cfg['color']};font-weight:600;'>"
                        f"{agent_cfg['name']} · {agent_cfg['role']}</span>",
                        unsafe_allow_html=True,
                    )
                st.markdown(msg["content"])
                for artifact in msg.get("_charts", []):
                    _render_artifact(artifact)

    if api_key:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;font-size:0.76rem;">'
            '<span style="color:#94B8C4;font-weight:600;">Tag agents:</span>'
            '<span style="background:#D6FFEA;border:1px solid #00E784;border-radius:10px;'
            'padding:1px 9px;color:#00493E;cursor:default;font-weight:500;">@Careem</span>'
            '<span style="background:#FFF3CD;border:1px solid #F5A623;border-radius:10px;'
            'padding:1px 9px;color:#8B6914;cursor:default;font-weight:500;">@Rashid</span>'
            '<span style="background:#DBEAFE;border:1px solid #3B82F6;border-radius:10px;'
            'padding:1px 9px;color:#1E40AF;cursor:default;font-weight:500;">@Noor</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        placeholder = f"Ask {active_cfg['name']}...  (@careem @rashid @noor to tag)"
        if prompt := st.chat_input(placeholder):
            mention_key, clean_prompt = parse_mention(prompt)
            effective_key = mention_key or active_key

            # User message
            st.session_state.chat_messages.append({
                "role": "user", "content": prompt,
            })

            # Render user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)

            # Primary agent response
            eff_cfg = AGENTS[effective_key]
            with st.chat_message("assistant", avatar=eff_cfg["avatar"]):
                st.markdown(
                    f"<span style='font-size:0.8rem;color:{eff_cfg['color']};font-weight:600;'>"
                    f"{eff_cfg['name']} · {eff_cfg['role']}</span>",
                    unsafe_allow_html=True,
                )
                with st.spinner(f"{eff_cfg['name']} is thinking..."):
                    try:
                        response, charts, consults = _run_agent_turn(
                            effective_key, clean_prompt,
                        )
                        st.markdown(response)
                        for artifact in charts:
                            _render_artifact(artifact)

                        st.session_state.chat_messages.append({
                            "role": "assistant", "agent": effective_key,
                            "content": response, "_charts": charts,
                        })

                        # [CONSULT:] auto-trigger
                        if consults and consults in AGENTS:
                            cons_cfg = AGENTS[consults]
                            cons_ctx = (
                                f"[WAR ROOM — You were consulted by {eff_cfg['name']} "
                                f"on the following question. Their response is below.\n\n"
                                f"User asked: {clean_prompt}\n\n"
                                f"--- {eff_cfg['name']}'s response ---\n{response}"
                            )
                            with st.chat_message("assistant", avatar=cons_cfg["avatar"]):
                                st.markdown(
                                    f"<span style='font-size:0.8rem;color:{cons_cfg['color']};font-weight:600;'>"
                                    f"{cons_cfg['name']} · {cons_cfg['role']}</span>",
                                    unsafe_allow_html=True,
                                )
                                with st.spinner(f"{cons_cfg['name']} is responding..."):
                                    try:
                                        c_resp, c_charts, _ = _run_agent_turn(
                                            consults, clean_prompt,
                                            extra_context=cons_ctx,
                                        )
                                        st.markdown(c_resp)
                                        for artifact in c_charts:
                                            _render_artifact(artifact)

                                        st.session_state.chat_messages.append({
                                            "role": "assistant", "agent": consults,
                                            "content": c_resp, "_charts": c_charts,
                                        })
                                    except Exception as e:
                                        st.error(f"{cons_cfg['name']}: {e}")

                    except Exception as e:
                        st.error(f"Failed: {e}")
    else:
        st.info(":material/lock: Set your API key in the sidebar to wake the agents up.", icon=":material/info:")

    if st.session_state.chat_messages and api_key:
        _, col_c = st.columns([10, 1])
        with col_c:
            if st.button(":material/delete:", help="Clear chat history"):
                st.session_state.chat_messages = []
                st.session_state.chat_initialized = False
                st.rerun()

elif explorer_page == "Store Map":
    from analysis.mapping import build_store_map

    st.subheader("Store Network — Dubai")
    st.caption("Click any store for performance details. Toggle layers for different views.")

    map_view = st.radio(
        "Map view",
        ["Health (RAG)", "Revenue", "Delivery zones"],
        horizontal=True,
        index=0,
        label_visibility="collapsed",
    )
    view_key = {"Health (RAG)": "health", "Revenue": "revenue", "Delivery zones": "delivery"}[map_view]

    focus = st.selectbox(
        "Focus on store",
        ["All stores"] + list(store_perf["store"].unique()),
        index=0,
        label_visibility="collapsed",
    )
    focus_store = None if focus == "All stores" else focus

    with st.spinner("Drawing store map..."):
        store_map = build_store_map(
            df=df,
            store_perf=store_perf,
            inv=inv,
            scorecard=scorecard,
            cat_perf=cat_perf,
            top=top,
            view=view_key,
            focus_store=focus_store,
        )
        html_str = getattr(store_map, "_repr_html_")()
        components.html(html_str, height=550, scrolling=False)

    with st.expander("Store KPIs"):
        kpi_data = store_perf[[
            "store", "total_revenue", "revenue_share", "stockout_rate",
        ]].copy()
        if scorecard and scorecard.get("summary"):
            kpi_data["health"] = kpi_data["store"].apply(
                lambda s: f"{scorecard['summary'].get(s, {}).get('health_pct', 100):.0f}%"
            )
        kpi_data["total_revenue"] = kpi_data["total_revenue"].apply(lambda x: f"${x:,.0f}")
        kpi_data["revenue_share"] = kpi_data["revenue_share"].apply(lambda x: f"{x:.0f}%")
        kpi_data["stockout_rate"] = kpi_data["stockout_rate"].apply(lambda x: f"{x:.1%}")
        st.dataframe(
            kpi_data,
            column_config={
                "store": "Store",
                "total_revenue": "Revenue",
                "revenue_share": "Share",
                "stockout_rate": "Stockout",
                "health": "Health score",
            },
            hide_index=True,
            width="stretch",
        )

elif explorer_page == "Overview":
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Revenue by category")
            chart_data = cat_perf.rename(columns={"category": "Category", "total_revenue": "Revenue"})
            st.bar_chart(chart_data, x="Category", y="Revenue", color="Category", stack=False)
    with col2:
        with st.container(border=True):
            st.subheader("Revenue by store")
            chart_data = store_perf.rename(columns={"store": "Store", "total_revenue": "Revenue"})
            st.bar_chart(chart_data, x="Store", y="Revenue", color="Store", stack=False)
    with st.container(border=True):
        st.subheader("Top SKUs by revenue")
        display_cols = {"sku": "SKU", "category": "Category", "total_units": "Units sold", "total_revenue": "Revenue",
                        "stockout_rate": "Stockout rate"}
        st.dataframe(top.head(10).rename(columns=display_cols),
                     column_config={"Revenue": st.column_config.NumberColumn(format="$%.0f"),
                                    "Stockout rate": st.column_config.NumberColumn(format="percent"),
                                    "Units sold": st.column_config.NumberColumn(format="%.0f")}, hide_index=True)
    with st.container(border=True):
        st.subheader("Category details")
        st.dataframe(cat_perf.rename(columns={"category": "Category", "total_revenue": "Revenue", "total_units": "Units", "avg_daily_units": "Avg daily", "stockout_rate": "Stockout rate", "promo_frequency": "Promo freq", "revenue_share": "Share (%)"}), column_config={"Revenue": st.column_config.NumberColumn(format="$%.0f"), "Stockout rate": st.column_config.NumberColumn(format="percent"), "Promo freq": st.column_config.NumberColumn(format="percent")}, hide_index=True)

elif explorer_page == "Category & stores":
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Revenue by category")
            st.bar_chart(cat_perf, x="category", y="total_revenue", color="category", stack=False)
    with col2:
        with st.container(border=True):
            st.subheader("Revenue by store")
            st.bar_chart(store_perf, x="store", y="total_revenue", color="store", stack=False)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Store breakdown")
            st.dataframe(store_perf.rename(columns={"store": "Store", "total_revenue": "Revenue", "total_units": "Units", "stockout_rate": "Stockout rate", "avg_units_per_day": "Avg daily", "revenue_share": "Share (%)"}), column_config={"Revenue": st.column_config.NumberColumn(format="$%.0f"), "Stockout rate": st.column_config.NumberColumn(format="percent")}, hide_index=True)
    with col2:
        with st.container(border=True):
            st.subheader("Category breakdown")
            st.dataframe(cat_perf.rename(columns={"category": "Category", "total_revenue": "Revenue", "total_units": "Units", "avg_daily_units": "Avg daily", "stockout_rate": "Stockout rate", "promo_frequency": "Promo freq", "revenue_share": "Share (%)"}), column_config={"Revenue": st.column_config.NumberColumn(format="$%.0f"), "Stockout rate": st.column_config.NumberColumn(format="percent"), "Promo freq": st.column_config.NumberColumn(format="percent")}, hide_index=True)

elif explorer_page == "Demand patterns":
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Demand by day of week")
            st.line_chart(weekday, x="day", y="avg_units")
    with col2:
        with st.container(border=True):
            st.subheader("Promotion impact")
            promo_chart = promo.copy()
            promo_chart["promotion"] = promo_chart["promotion"].map({True: "Promo", False: "Regular"})
            st.bar_chart(promo_chart, x="promotion", y="avg_units_sold", color="promotion", stack=False)
    if lift != 0:
        st.info(f"Promotions drive **{lift}% higher** units sold on average.", icon=":material/trending_up:")
    with st.container(border=True):
        st.subheader("Daily demand (last 30 days)")
        recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=30)]
        daily = recent.groupby("date").agg(units_sold=("units_sold", "sum"), revenue=("revenue", "sum")).reset_index().sort_values("date")
        st.line_chart(daily.set_index("date"))

elif explorer_page == "Inventory health":
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Service level by category")
            inv_vis = inv_summary.rename(columns={"category": "Category", "avg_service_level": "Service level (%)"})
            st.bar_chart(inv_vis, x="Category", y="Service level (%)", color="Category", stack=False)
    with col2:
        with st.container(border=True):
            st.subheader("Stockout days by category")
            st.bar_chart(inv_summary, x="category", y="total_stockout_days", color="category", stack=False)
    with st.container(border=True):
        st.subheader("SKU-level inventory health")
        col_filter = st.selectbox("Filter by category", options=["All"] + sorted(df["category"].unique()), label_visibility="collapsed")
        filtered_inv = inv if col_filter == "All" else inv[inv["category"] == col_filter]
        st.dataframe(filtered_inv[["store", "sku", "category", "daily_avg_units", "service_level", "safety_stock", "reorder_point", "stockout_days"]].rename(columns={"store": "Store", "sku": "SKU", "category": "Category", "daily_avg_units": "Avg daily", "service_level": "Service level", "safety_stock": "Safety stock", "reorder_point": "Reorder point", "stockout_days": "Stockout days"}).sort_values("Stockout days", ascending=False), column_config={"Service level": st.column_config.NumberColumn(format="percent")}, hide_index=True)
    if flags:
        risk_df = pd.DataFrame(flags)
        st.subheader("Risk flags")
        st.data_editor(risk_df[["store", "sku", "category", "risk", "metric", "detail"]].rename(columns={"store": "Store", "sku": "SKU", "category": "Category", "risk": "Risk", "metric": "Metric", "detail": "Detail"}), disabled=True, hide_index=True)

elif explorer_page == "Forecast":
    store_select = st.selectbox("Select store", options=list(forecast.keys()), label_visibility="collapsed")
    data = forecast[store_select]
    hist = data["historical"]
    fcast_vals = data["forecast"]
    col1, col2 = st.columns([3, 2])
    with col1:
        if fcast_vals:
            last_date = pd.to_datetime(hist["date"].iloc[-1])
            fcast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=len(fcast_vals))
            fcast_df = pd.DataFrame({"date": fcast_dates, "units_sold": fcast_vals, "type": "Forecast"})
            hist_df = hist.copy()
            hist_df["type"] = "Historical"
            color_scale = alt.Scale(domain=["Historical", "Forecast"], range=["#00E784", "#A6EDF2"])
            hist_line = alt.Chart(hist_df).mark_line(point=False).encode(x=alt.X("date:T", title="Date"), y=alt.Y("units_sold:Q", title="Units sold"), color=alt.Color("type:N", scale=color_scale))
            fcast_line = alt.Chart(fcast_df).mark_line(strokeDash=[8, 4], point=False).encode(x=alt.X("date:T", title="Date"), y=alt.Y("units_sold:Q", title="Units sold"), color=alt.Color("type:N", scale=color_scale))
            final_chart = alt.layer(hist_line, fcast_line).properties(title=f"14-day demand forecast — {store_select}", height=380)
            st.altair_chart(final_chart, width="stretch")
        else:
            st.info("Not enough data to generate a forecast for this store.")
    with col2:
        with st.container(border=True):
            st.subheader("14-day outlook")
            outlook = pd.DataFrame([{"Store": s, "Forecasted units": d["next_14d_total"]} for s, d in forecast.items()])
            st.dataframe(outlook, column_config={"Forecasted units": st.column_config.NumberColumn(format="%.0f")}, hide_index=True)
        with st.container(border=True):
            st.subheader("Confidence")
            conf_data = []
            for c in forec_conf:
                conf_data.append({"Store": c["store"], "Confidence": c.get("confidence", "?"), "Volatility": c.get("daily_volatility", 0)})
            st.dataframe(pd.DataFrame(conf_data), hide_index=True)

elif explorer_page == "S&OP Scorecard":
    st.subheader("RAG health scorecard")
    rag_data = scorecard["summary"]
    store_names = sorted(rag_data.keys())
    rag_cols = st.columns(len(store_names))
    for i, store in enumerate(store_names):
        d = rag_data[store]
        with rag_cols[i]:
            with st.container(border=True):
                st.markdown(f"**{store}**")
                st.metric("Health", f"{d['health_pct']:.0f}%")
                st.markdown(f":green_circle: {d['green']}  :orange_circle: {d['amber']}  :red_circle: {d['red']}")
    st.divider()
    st.subheader("SKU-level RAG status")
    store_filter = st.selectbox("Filter by store", options=["All"] + store_names, label_visibility="collapsed", key="rag_filter")
    filtered = scorecard["items"] if store_filter == "All" else [r for r in scorecard["items"] if r["store"] == store_filter]
    rag_df = pd.DataFrame(filtered).sort_values("revenue_at_risk", ascending=False)
    rag_df = rag_df.rename(columns={"store": "Store", "sku": "SKU", "category": "Category", "status": "RAG", "service_level": "Service level", "stockout_days": "Stockout days", "revenue_at_risk": "$ at risk"})

    def highlight_rag(series):
        def _style(v):
            if v == "GREEN":
                return "background-color: #D6FFEA; color: #00493E; font-weight: 600"
            if v == "AMBER":
                return "background-color: #FFF7ED; color: #9A3412; font-weight: 600"
            if v == "RED":
                return "background-color: #FEF2F2; color: #991B1B; font-weight: 600"
            return ""
        return series.map(_style)

    styled = rag_df.style.apply(highlight_rag, subset=["RAG"])
    st.dataframe(styled, column_config={"Service level": st.column_config.NumberColumn(format="%.1f%%"), "$ at risk": st.column_config.NumberColumn(format="$%.0f")}, hide_index=True)

    st.divider()
    st.subheader("Scenario simulator")
    st.caption("Adjust parameters to see projected impact")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        promo_mult = st.slider("Promo uplift", 0.5, 3.0, 1.5, 0.1, format="%.1fx")
    with sc2:
        demand_growth = st.slider("Demand growth", -20.0, 30.0, 0.0, 1.0, format="%+.1f%%")
    with sc3:
        lead_time = st.slider("Lead time (days)", 1, 7, 3, 1)
    with sc4:
        safety_factor = st.slider("Safety stock factor", 0.5, 3.0, 1.0, 0.1, format="%.1fx")

    scenario = run_scenario(df, forecast, inv, {"promo_mult": promo_mult, "demand_growth": demand_growth, "lead_time": lead_time, "safety_factor": safety_factor})
    st.divider()
    base = scenario["base"]
    proj = scenario["projected"]
    delta = scenario["delta"]
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric("Revenue", f"${proj['total_revenue']:,.0f}", f"{delta['revenue_change_pct']:+.1f}%", border=True)
    with sc2:
        st.metric("14-day forecast", f"{proj['forecast_14d']:,} units", f"{delta['forecast_change_pct']:+.1f}%", border=True)
    with sc3:
        st.metric("Stockout rate", f"{proj['stockout_rate']}%", f"{proj['stockout_rate'] - base['stockout_rate']:+.1f}pp", border=True, delta_color="inverse")
    with sc4:
        st.metric("Safety stock", f"{proj['safety_stock_days']:,.0f} units/day", border=True)

st.caption("Auto-Analyst — Built for Careem Grocery Supply Chain Challenge")
