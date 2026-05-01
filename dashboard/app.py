"""
Streamlit admin console for SME Indicators.

Role: data ops only — trigger scrape / parse / compute, watch pipeline status,
inspect freshness and gaps. Charts live in the React viewer.

Run locally:
    streamlit run dashboard/app.py

Run against a remote API (e.g. EC2):
    SME_ADMIN_API_URL=http://98.81.94.194 streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# Make project root importable when launched from dashboard/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from storage.database import init_db, query  # noqa: E402

st.set_page_config(
    page_title="SME Indicators — Admin",
    page_icon="🛠️",
    layout="wide",
)

API_URL = os.getenv("SME_ADMIN_API_URL", "").rstrip("/")
REMOTE_MODE = bool(API_URL)

# ── In-process pipeline runner (local mode) ─────────────────────────────────

_local_state: dict = {"status": "idle", "message": "", "started_at": None}
_local_lock = threading.Lock()


def _run_local(stages: list[str], days: int) -> None:
    """Run agent.py stages in a background thread, mirroring api.routers.pipeline."""
    try:
        # Force UTF-8 stdout so scrapers can print without cp1252 errors on Windows
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")

        if "scrape" in stages:
            _local_state["message"] = f"Scraping (last {days} days)…"
            from agent import run_scrape
            run_scrape(days)

        if "parse" in stages:
            _local_state["message"] = "Parsing PDFs & XBRL…"
            from agent import run_parse
            run_parse()

        if "compute" in stages:
            _local_state["message"] = "Computing indicators…"
            from agent import run_compute
            run_compute()

        _local_state["status"] = "idle"
        _local_state["message"] = f"Done — last run {datetime.now().strftime('%H:%M:%S')}"
    except Exception as exc:  # noqa: BLE001
        _local_state["status"] = "error"
        _local_state["message"] = f"{type(exc).__name__}: {exc}"


def trigger_local(stages: list[str], days: int) -> tuple[bool, str]:
    with _local_lock:
        if _local_state["status"] == "running":
            return False, "Pipeline already running"
        _local_state["status"] = "running"
        _local_state["started_at"] = datetime.now().isoformat()
        _local_state["message"] = "Starting…"
        threading.Thread(
            target=_run_local, args=(stages, days), daemon=True
        ).start()
    return True, "Pipeline started"


def status_local() -> dict:
    return dict(_local_state)


# ── Remote pipeline runner (EC2 / API mode) ─────────────────────────────────


def trigger_remote(use_ai: bool) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_URL}/api/pipeline/run",
            json={"use_ai_parser": use_ai},
            timeout=10,
        )
        r.raise_for_status()
        body = r.json()
        return bool(body.get("ok", False)), str(body.get("message", ""))
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def set_remote_parser_mode(use_ai: bool) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_URL}/api/pipeline/parser-mode",
            json={"use_ai_parser": use_ai},
            timeout=10,
        )
        r.raise_for_status()
        body = r.json()
        return bool(body.get("ok", False)), f"Remote parser mode: {'AI' if body.get('use_ai_parser') else 'regex'}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def status_remote() -> dict:
    try:
        r = requests.get(f"{API_URL}/api/pipeline/status", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"{type(exc).__name__}: {exc}"}


def fetch_health_remote() -> dict:
    try:
        r = requests.get(f"{API_URL}/api/health/data", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}


# ── Local DB snapshot (used in local mode) ──────────────────────────────────


def fetch_health_local() -> dict:
    init_db()
    rows = query("""
        SELECT
            (SELECT COUNT(*) FROM raw_filings)                          AS total_filings,
            (SELECT COUNT(*) FROM filing_signals)                       AS pdf_parsed,
            (SELECT COUNT(*) FROM financials)                           AS xbrl_parsed,
            (SELECT COUNT(*) FROM indicators)                           AS indicator_rows,
            (SELECT CAST(MAX(filing_date) AS VARCHAR) FROM raw_filings) AS latest_filing,
            (SELECT CAST(MAX(scraped_at)  AS VARCHAR) FROM raw_filings) AS last_scrape,
            (SELECT CAST(MAX(computed_at) AS VARCHAR) FROM indicators)  AS last_compute
    """)
    snap = rows.iloc[0].to_dict() if not rows.empty else {}
    total = snap.get("total_filings") or 0
    parsed = snap.get("pdf_parsed") or 0
    snap["pdf_parse_coverage_pct"] = round(parsed / total * 100, 2) if total else 0
    return snap


# ── Sidebar ─────────────────────────────────────────────────────────────────

st.sidebar.title("🛠️ SME Indicators — Admin")
st.sidebar.caption("Data refresh & pipeline ops")

mode_label = "Remote (API)" if REMOTE_MODE else "Local (in-process)"
st.sidebar.markdown(f"**Mode:** `{mode_label}`")
if REMOTE_MODE:
    st.sidebar.markdown(f"**API:** `{API_URL}`")
else:
    st.sidebar.caption("Set `SME_ADMIN_API_URL` to drive a remote API.")

st.sidebar.markdown("---")

days_back = st.sidebar.slider(
    "Scrape lookback (days)", 7, 365, 90, step=7,
    help="Used by the Scrape stage. Ignored in remote mode (server uses its own default).",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Parser")

# Default the toggle from the current config flag (env var on first load,
# session state on subsequent reruns)
if "use_ai_parser" not in st.session_state:
    st.session_state["use_ai_parser"] = bool(getattr(config, "USE_AI_PARSER", True))

use_ai_parser = st.sidebar.toggle(
    "Use OpenAI parser (gpt-4o-mini)",
    value=st.session_state["use_ai_parser"],
    help=(
        "ON: PyMuPDF text → GPT-4o-mini structured JSON extraction.\n"
        "OFF: regex keyword scan + pdfplumber tables.\n"
        "Falls back to regex automatically if OPENAI_API_KEY is unset."
    ),
)
st.session_state["use_ai_parser"] = use_ai_parser

# Apply locally so the next pipeline trigger picks it up
config.USE_AI_PARSER = use_ai_parser

if REMOTE_MODE:
    st.sidebar.caption(
        "Toggle is sent with every Run; click below to push it without a run."
    )
    if st.sidebar.button("Apply parser mode to remote", use_container_width=True):
        ok, msg = set_remote_parser_mode(use_ai_parser)
        (st.sidebar.success if ok else st.sidebar.error)(msg)
else:
    st.sidebar.caption(
        f"Active mode: **{'OpenAI' if use_ai_parser else 'regex / pdfplumber'}**"
    )

st.sidebar.markdown("---")
st.sidebar.caption(f"Now: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── Header ──────────────────────────────────────────────────────────────────

st.title("SME Indicators — Admin Console")
st.write(
    "Trigger and monitor the data pipeline. The end-user dashboard lives "
    "in the React app served at `/` on the API server."
)

# ── Pipeline controls ───────────────────────────────────────────────────────

st.subheader("Pipeline controls")

c1, c2, c3, c4 = st.columns(4)

if REMOTE_MODE:
    if c1.button("▶ Run full pipeline (remote)", use_container_width=True, type="primary"):
        ok, msg = trigger_remote(use_ai_parser)
        (st.success if ok else st.error)(msg)
    c2.button("Scrape only", disabled=True, use_container_width=True,
              help="Per-stage trigger not exposed by the remote API. Use full pipeline.")
    c3.button("Parse only", disabled=True, use_container_width=True)
    c4.button("Compute only", disabled=True, use_container_width=True)
else:
    if c1.button("▶ Full pipeline", use_container_width=True, type="primary"):
        ok, msg = trigger_local(["scrape", "parse", "compute"], days_back)
        (st.success if ok else st.warning)(msg)
    if c2.button("Scrape", use_container_width=True):
        ok, msg = trigger_local(["scrape"], days_back)
        (st.success if ok else st.warning)(msg)
    if c3.button("Parse", use_container_width=True):
        ok, msg = trigger_local(["parse"], days_back)
        (st.success if ok else st.warning)(msg)
    if c4.button("Compute", use_container_width=True):
        ok, msg = trigger_local(["compute"], days_back)
        (st.success if ok else st.warning)(msg)

# ── Live status ─────────────────────────────────────────────────────────────

st.subheader("Pipeline status")

state = status_remote() if REMOTE_MODE else status_local()
status = state.get("status", "unknown")
badge = {"running": "🟡", "idle": "🟢", "error": "🔴"}.get(status, "⚪")

s1, s2, s3 = st.columns(3)
s1.metric("Status", f"{badge} {status}")
s2.metric("Message", state.get("message") or "—")
s3.metric("Started at", state.get("started_at") or "—")

if status == "running":
    st.info("Pipeline is running. This page auto-refreshes every 5 seconds.")
    # Poll
    import time
    time.sleep(5)
    st.rerun()

# ── Freshness panel ─────────────────────────────────────────────────────────

st.subheader("Data freshness")

snap = fetch_health_remote() if REMOTE_MODE else fetch_health_local()

if snap.get("status") == "error":
    st.error(f"Could not load freshness: {snap.get('message')}")
else:
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total filings", int(snap.get("total_filings") or 0))
    f2.metric("PDF parsed", int(snap.get("pdf_parsed") or 0),
              f"{snap.get('pdf_parse_coverage_pct', 0)}% coverage")
    f3.metric("XBRL parsed", int(snap.get("xbrl_parsed") or 0))
    f4.metric("Indicator rows", int(snap.get("indicator_rows") or 0))

    g1, g2, g3 = st.columns(3)
    g1.metric("Latest filing", snap.get("latest_filing") or "—")
    g2.metric("Last scrape", snap.get("last_scrape") or "—")
    g3.metric("Last compute", snap.get("last_compute") or "—")

# ── Data preview (local mode only — direct DB) ──────────────────────────────

if not REMOTE_MODE:
    st.subheader("Data preview")

    tabs = st.tabs(["Indicators", "Recent filings", "Financials"])

    with tabs[0]:
        df = query("""
            SELECT sector, composite_score,
                   revenue_momentum, margin_pressure, order_book_signal,
                   credit_stress, capex_intentions, export_outlook,
                   as_of_date, computed_at
            FROM indicators
            ORDER BY composite_score DESC
        """)
        if df.empty:
            st.info("No indicator rows yet. Run **Compute** after parsing.")
        else:
            st.dataframe(df, use_container_width=True, height=320)

    with tabs[1]:
        df = query("""
            SELECT exchange, company_name, filing_date, category, headline
            FROM raw_filings
            ORDER BY filing_date DESC
            LIMIT 200
        """)
        if df.empty:
            st.info("No filings scraped yet.")
        else:
            st.dataframe(df, use_container_width=True, height=320)

    with tabs[2]:
        df = query("""
            SELECT f.filing_id, r.company_name, r.exchange,
                   f.revenue, f.ebitda, f.pat, f.total_debt,
                   f.period_end, f.period_type
            FROM financials f
            LEFT JOIN raw_filings r ON r.id = f.filing_id
            ORDER BY f.period_end DESC NULLS LAST
            LIMIT 200
        """)
        if df.empty:
            st.info("No XBRL financials parsed yet.")
        else:
            st.dataframe(df, use_container_width=True, height=320)
else:
    st.caption(
        "Data preview tables are hidden in remote mode (they require direct DB access). "
        "Use the React viewer at the API URL to inspect data."
    )
