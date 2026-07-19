# Auto-Analyst — Careem Grocery

**AI-powered demand planning dashboard with a multi-agent executive War Room.**

Three AI personas — **Careem** (S&OP Lead), **Rashid** (CFO), and **Noor** (Ops Lead) — analyze live demand, inventory, and forecast data through their domain lens. Each has a distinct Emirati voice, proverb collection, and can autonomously consult the others. The result is a collaborative decision environment that mirrors how a real executive team works.

---

## ✨ Features

| Category | Capabilities |
|---|---|
| **Multi-Agent War Room** | 3 AI personas with unique voices, domain proverbs, avatars, and color-coded chat bubbles |
| **Agent Cooperation** | Careem autonomously consults Rashid (margins) or Noor (ops) via `[CONSULT:]` triggers |
| **@mention** | Tag any agent mid-conversation to redirect the question |
| **Live Chat Tools** | Agents call `generate_plot` (9 chart types) and `show_map` (interactive Dubai store map) |
| **Store Map** | 5 Dubai dark stores on an interactive Folium map — RAG health pins, delivery zones, click pop-ups |
| **Mood Meter** | Careem's live emotional state based on anomaly rate, service levels, and critical flags |
| **Boardroom Mode** | Clean presentation view of the full conversation for S&OP meetings |
| **Overview Dashboard** | KPI cards, demand trend, category breakdown, mood meter |
| **Data Explorer** | Category & stores, demand patterns, inventory health, forecast, S&OP scorecard (RAG) |
| **Anomaly Detection** | Statistical anomaly flagging with alert cards |
| **Scenario Simulation** | What-if analysis — promo boost, demand growth, safety stock changes |
| **Dark Theme** | Midnight Blue (#001942) with Careem green (#00E784) accents |

---

## 🤖 The War Room

| | Careem | Rashid | Noor |
|---|---|---|---|
| **Role** | S&OP Lead | CFO | Ops Lead |
| **Voice** | "Captain" | "Partner" | "Team" |
| **Domain** | Demand, inventory, forecast | Margins, unit economics, ROI | Delivery SLA, fleet, staffing |
| **Proverbs** | *"Trust Allah but tie your camel..."* | *"Revenue is vanity, margin is sanity."* | *"You can't deliver from an empty shelf."* |
| **Consult trigger** | Calls Rashid / Noor | Responds to Careem / Noor | Responds to Careem / Rashid |
| **Tools** | generate_plot, show_map | generate_plot, show_map | generate_plot, show_map |

---

## 📁 Project Structure

```
Auto-Analyst/
├── app.py                     # Streamlit entry point — sidebar, pages, chat loop
├── insights/
│   ├── agents.py              # 3 agent configs — prompts, avatars, proverbs, @mention/consult parsers
│   ├── chat.py                # LLM call orchestration, tools schema, plot generation, map generation
├── analysis/
│   ├── stats.py               # Summary stats, category/store performance, promo lift, gaps
│   ├── forecast.py            # 14-day rolling forecast per store with confidence tiers
│   ├── inventory.py            # Service level, safety stock, reorder points, risk flags, tiered risks
│   ├── scorecard.py           # RAG scorecard — per-store health percentages
│   ├── scenario.py            # What-if scenario runner — base vs projected deltas
│   ├── anomaly.py             # Statistical anomaly detection on demand patterns
│   └── mapping.py             # Interactive Folium map — store coords, delivery zones, RAG pins
├── data/
│   ├── generate_data.py       # Synthetic grocery demand generator (5 stores, 25 SKUs, 5 categories)
│   └── sample_grocery_data.csv  # 22,500 rows — ready to use
├── assets/
│   └── avatars/               # Agent headshot images (PNG / SVG)
├── .streamlit/
│   ├── config.toml            # Midnight Blue theme — all colors
│   └── secrets.toml           # API key (gitignored — use Streamlit Cloud secrets for deployment)
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

```bash
# Clone and install
git clone <your-repo-url> auto-analyst
cd auto-analyst

uv venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

uv pip install -r requirements.txt

# Run
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## 🔑 API Key Setup

The dashboard works **without an API key** — all charts, maps, tables, and analysis load. To unlock the AI agents:

### Option 1: `.streamlit/secrets.toml` (local dev)

```toml
LLM_API_KEY = "sk-your-api-key"
LLM_API_BASE = "https://api.openai.com/v1"
LLM_MODEL = "gpt-4o-mini"
```

### Option 2: Environment variables

```powershell
$env:LLM_API_KEY = "sk-..."
$env:LLM_API_BASE = "https://api.openai.com/v1"
$env:LLM_MODEL = "deepseek-v4-flash"
```

### Option 3: Manual sidebar entry

Select a provider from the sidebar dropdown and paste your key. Works with OpenAI, DeepSeek, Anthropic (OpenRouter), Groq, Together, and any custom OpenAI-compatible endpoint.

---

## 🌐 Deploy (Streamlit Cloud — free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → main file: `app.py`
4. Under **Advanced settings**, add your secrets:

```
LLM_API_KEY = "sk-..."
LLM_API_BASE = "https://api.openai.com/v1"
LLM_MODEL = "gpt-4o-mini"
```

5. Deploy → your app is live at `https://your-app.streamlit.app`

---

## 📸 Screenshots to capture

| Feature | What to capture |
|---|---|
| **Overview** | KPI cards, mood meter, demand sparkline, category mini-chart |
| **War Room** | 3 agent cards + chat showing Careem consulting Rashid |
| **Store Map** | Dubai map with 5 store pins, delivery zones, RAG coloring |
| **Chat with chart** | Agent response with an inline altair chart rendered below |
| **Boardroom Mode** | Clean view showing multi-agent conversation history |
| **@mention** | Chat showing `@rashid what's the margin on this?` |

---

## 🎯 Job Fit

| JD Requirement | Demonstrated by |
|---|---|
| Forecasting & Modelling | 14-day rolling forecast per store with confidence tiers |
| Demand Variability | Weekday patterns, promo lift, anomaly detection |
| S&OP Process Leadership | Multi-agent War Room simulating cross-functional review |
| Inventory Optimisation | Safety stock, reorder points, service level tracking, RAG scorecard |
| Data & Tooling | Pandas, Altair, Folium, multi-provider LLM integration, Streamlit |
| Insight & Communication | Narrative briefs in character voice, boardroom-ready presentation mode |
| Innovation & AI | Function-calling agents, autonomous agent consultation, real-time tool use |

---

## 📄 License

MIT — use it, fork it, adapt it for your own supply chain challenges.
