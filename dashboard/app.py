"""
Streamlit dashboard for SME Indicators.
Run with: streamlit run dashboard/app.py
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path so imports work when launched from dashboard/
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import init_db, query

st.set_page_config(
    page_title="SME Indicators Dashboard",
    page_icon="📊",
    layout="wide",
)

init_db()

# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("SME Indicators")
st.sidebar.markdown("Corporate filing signals from BSE & NSE")

days_back = st.sidebar.slider("Lookback (days)", 30, 365, 90, step=30)
exchange_filter = st.sidebar.multiselect(
    "Exchange", ["BSE", "NSE"], default=["BSE", "NSE"]
)

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    with st.spinner("Running full pipeline (scrape → parse → compute)..."):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "agent.py"),
             "--scrape", "--parse", "--compute",
             "--days", str(days_back)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            st.sidebar.success("Data refreshed successfully")
        else:
            st.sidebar.error(f"Pipeline error:\n{result.stderr[-500:]}")

st.sidebar.markdown("---")
st.sidebar.caption(f"As of {date.today()}")

# ── Load Data ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_indicators():
    return query("SELECT * FROM indicators ORDER BY composite_score DESC")

@st.cache_data(ttl=300)
def load_recent_filings(days: int, exchanges: list):
    if not exchanges:
        return pd.DataFrame()
    exc_list = ", ".join(f"'{e}'" for e in exchanges)
    return query(f"""
        SELECT rf.company_name, rf.exchange, rf.filing_date,
               rf.category, rf.headline,
               fs.order_book, fs.capex, fs.credit_stress, fs.export
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE rf.filing_date >= CURRENT_DATE - INTERVAL {days} DAY
          AND rf.exchange IN ({exc_list})
        ORDER BY rf.filing_date DESC
        LIMIT 100
    """)

@st.cache_data(ttl=300)
def load_indicator_history():
    return query("""
        SELECT sector, as_of_date,
               revenue_momentum, margin_pressure, order_book_signal,
               credit_stress, capex_intentions, export_outlook, composite_score
        FROM indicators
        ORDER BY as_of_date
    """)

indicators_df = load_indicators()
filings_df = load_recent_filings(days_back, exchange_filter)
history_df = load_indicator_history()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 SME Leading Indicators")
st.markdown("Derived from BSE India & NSE corporate filings")

if indicators_df.empty:
    st.info("No indicator data yet. Click **Refresh Data** in the sidebar to run the pipeline.")
    st.stop()

# ── Composite Score Gauge ─────────────────────────────────────────────────────

overall_score = indicators_df["composite_score"].mean()

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(overall_score, 1),
        title={"text": "Composite SME Health Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1f77b4"},
            "steps": [
                {"range": [0, 33], "color": "#ff4444"},
                {"range": [33, 66], "color": "#ffaa00"},
                {"range": [66, 100], "color": "#44bb44"},
            ],
        },
    ))
    fig_gauge.update_layout(height=250, margin=dict(t=40, b=0, l=20, r=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    best = indicators_df.iloc[0]
    st.metric("Top Sector", best["sector"], f"{best['composite_score']:.1f}/100")
    total_filings = query("SELECT COUNT(*) AS n FROM raw_filings").iloc[0]["n"]
    st.metric("Total Filings", int(total_filings))

with col3:
    signals_df = query("""
        SELECT
            SUM(CAST(order_book AS INTEGER))  AS order_book,
            SUM(CAST(capex AS INTEGER))       AS capex,
            SUM(CAST(credit_stress AS INTEGER)) AS credit_stress,
            SUM(CAST(export AS INTEGER))      AS export
        FROM filing_signals
    """)
    if not signals_df.empty:
        row = signals_df.iloc[0]
        st.metric("Order Book Mentions", int(row.get("order_book") or 0))
        st.metric("Capex Mentions", int(row.get("capex") or 0))

# ── Sector Heatmap ────────────────────────────────────────────────────────────

st.markdown("### Sector Breakdown")

indicator_cols = [
    "revenue_momentum", "margin_pressure", "order_book_signal",
    "credit_stress", "capex_intentions", "export_outlook",
]
heat_df = indicators_df[["sector"] + indicator_cols].set_index("sector")

fig_heat = px.imshow(
    heat_df.fillna(50),
    color_continuous_scale="RdYlGn",
    zmin=0, zmax=100,
    labels={"color": "Score (0–100)"},
    aspect="auto",
)
fig_heat.update_layout(height=max(300, len(heat_df) * 40), margin=dict(t=20, b=20))
st.plotly_chart(fig_heat, use_container_width=True)

# ── Indicator Trend Lines ─────────────────────────────────────────────────────

st.markdown("### Composite Score by Sector")

if not history_df.empty and len(history_df["as_of_date"].unique()) > 1:
    fig_trend = px.line(
        history_df,
        x="as_of_date", y="composite_score", color="sector",
        labels={"as_of_date": "Date", "composite_score": "Score"},
    )
    fig_trend.update_layout(height=350)
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    fig_bar = px.bar(
        indicators_df.sort_values("composite_score"),
        x="composite_score", y="sector",
        orientation="h",
        color="composite_score",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        labels={"composite_score": "Score", "sector": "Sector"},
    )
    fig_bar.update_layout(height=max(300, len(indicators_df) * 35), showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Recent Filings Table ───────────────────────────────────────────────────────

st.markdown("### Recent Filings with Signal Flags")

if filings_df.empty:
    st.info("No filings loaded for the selected filters.")
else:
    def _flag(val):
        return "✅" if val else ""

    display = filings_df.copy()
    for col in ["order_book", "capex", "credit_stress", "export"]:
        if col in display.columns:
            display[col] = display[col].apply(_flag)

    st.dataframe(
        display,
        use_container_width=True,
        height=400,
        column_config={
            "headline": st.column_config.TextColumn("Headline", width="large"),
            "filing_date": st.column_config.DateColumn("Date"),
            "order_book": st.column_config.TextColumn("Order Book"),
            "capex": st.column_config.TextColumn("Capex"),
            "credit_stress": st.column_config.TextColumn("Credit Stress"),
            "export": st.column_config.TextColumn("Export"),
        },
    )
