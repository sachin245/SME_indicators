"""
Indicators engine — computes 7 leading SME indicators from parsed filing data.
All indicators are normalized to 0–100. Credit Stress is inverted (higher = worse).
Results are aggregated by sector and stored in the `indicators` table.
"""

import hashlib
from datetime import date

import pandas as pd
import numpy as np

from config import INDICATOR_WEIGHTS
from storage.database import query, upsert_indicators


def _indicator_id(sector: str, as_of_date: str) -> str:
    return hashlib.md5(f"{sector}|{as_of_date}".encode()).hexdigest()


def _normalize(series: pd.Series, invert: bool = False) -> pd.Series:
    """Min-max normalize to 0–100. Invert for stress indicators."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(50.0, index=series.index)
    norm = (series - mn) / (mx - mn) * 100
    return (100 - norm) if invert else norm


# ── Revenue Momentum (XBRL financials) ──────────────────────────────────────

def compute_revenue_momentum() -> pd.DataFrame:
    """QoQ revenue growth rate per sector, normalized 0–100."""
    df = query("""
        SELECT sector,
               period_end,
               SUM(revenue) AS total_revenue
        FROM financials
        WHERE revenue IS NOT NULL
        GROUP BY sector, period_end
        ORDER BY sector, period_end
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "revenue_momentum"])

    df["prev_revenue"] = df.groupby("sector")["total_revenue"].shift(1)
    df["growth"] = (df["total_revenue"] - df["prev_revenue"]) / df["prev_revenue"].replace(0, np.nan)
    latest = df.groupby("sector")["growth"].last().reset_index()
    latest["revenue_momentum"] = _normalize(latest["growth"].fillna(0))
    return latest[["sector", "revenue_momentum"]]


# ── Margin Pressure (XBRL financials) ───────────────────────────────────────

def compute_margin_pressure() -> pd.DataFrame:
    """EBITDA margin trend — higher margin = higher score."""
    df = query("""
        SELECT sector,
               period_end,
               SUM(ebitda)  AS total_ebitda,
               SUM(revenue) AS total_revenue
        FROM financials
        WHERE ebitda IS NOT NULL AND revenue IS NOT NULL AND revenue > 0
        GROUP BY sector, period_end
        ORDER BY sector, period_end
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "margin_pressure"])

    df["margin"] = df["total_ebitda"] / df["total_revenue"]
    latest = df.groupby("sector")["margin"].last().reset_index()
    latest["margin_pressure"] = _normalize(latest["margin"].fillna(0))
    return latest[["sector", "margin_pressure"]]


# ── Order Book Signal (filing keyword flags) ────────────────────────────────

def compute_order_book_signal() -> pd.DataFrame:
    """% of recent filings per sector with order book mentions."""
    df = query("""
        SELECT sector,
               COUNT(*)                          AS total,
               SUM(CAST(order_book AS INTEGER))  AS hits
        FROM filing_signals
        WHERE filing_date >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY sector
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "order_book_signal"])

    df["rate"] = df["hits"] / df["total"].replace(0, np.nan)
    df["order_book_signal"] = _normalize(df["rate"].fillna(0))
    return df[["sector", "order_book_signal"]]


# ── Credit Stress Index (inverted) ──────────────────────────────────────────

def compute_credit_stress() -> pd.DataFrame:
    """% of filings with credit stress mentions — inverted so higher = better."""
    df = query("""
        SELECT sector,
               COUNT(*)                               AS total,
               SUM(CAST(credit_stress AS INTEGER))    AS hits
        FROM filing_signals
        WHERE filing_date >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY sector
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "credit_stress"])

    df["rate"] = df["hits"] / df["total"].replace(0, np.nan)
    df["credit_stress"] = _normalize(df["rate"].fillna(0), invert=True)
    return df[["sector", "credit_stress"]]


# ── Capex Intentions Index ───────────────────────────────────────────────────

def compute_capex_intentions() -> pd.DataFrame:
    """% of filings with capex mentions."""
    df = query("""
        SELECT sector,
               COUNT(*)                        AS total,
               SUM(CAST(capex AS INTEGER))     AS hits
        FROM filing_signals
        WHERE filing_date >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY sector
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "capex_intentions"])

    df["rate"] = df["hits"] / df["total"].replace(0, np.nan)
    df["capex_intentions"] = _normalize(df["rate"].fillna(0))
    return df[["sector", "capex_intentions"]]


# ── Export Outlook Index ─────────────────────────────────────────────────────

def compute_export_outlook() -> pd.DataFrame:
    """% of filings with export/forex mentions."""
    df = query("""
        SELECT sector,
               COUNT(*)                         AS total,
               SUM(CAST(export AS INTEGER))     AS hits
        FROM filing_signals
        WHERE filing_date >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY sector
    """)
    if df.empty:
        return pd.DataFrame(columns=["sector", "export_outlook"])

    df["rate"] = df["hits"] / df["total"].replace(0, np.nan)
    df["export_outlook"] = _normalize(df["rate"].fillna(0))
    return df[["sector", "export_outlook"]]


# ── Composite Score ──────────────────────────────────────────────────────────

def compute_composite(merged: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=merged.index)
    for field, weight in INDICATOR_WEIGHTS.items():
        if field in merged.columns:
            score += merged[field].fillna(50) * weight
    return score


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    """Compute all indicators and persist to the indicators table."""
    print("[Engine] Computing indicators...")

    frames = [
        compute_revenue_momentum(),
        compute_margin_pressure(),
        compute_order_book_signal(),
        compute_credit_stress(),
        compute_capex_intentions(),
        compute_export_outlook(),
    ]

    # Merge all on sector
    merged = frames[0]
    for df in frames[1:]:
        if df.empty:
            continue
        merged = merged.merge(df, on="sector", how="outer")

    if merged.empty:
        print("[Engine] No data to compute indicators from — run scrape and parse first")
        return

    merged["composite_score"] = compute_composite(merged)
    merged["as_of_date"] = str(date.today())
    merged["id"] = merged.apply(
        lambda r: _indicator_id(r["sector"], r["as_of_date"]), axis=1
    )
    merged["computed_at"] = None

    cols = [
        "id", "sector", "as_of_date",
        "revenue_momentum", "margin_pressure", "order_book_signal",
        "credit_stress", "capex_intentions", "export_outlook",
        "composite_score", "computed_at",
    ]
    for col in cols:
        if col not in merged.columns:
            merged[col] = None

    upsert_indicators(merged[cols].to_dict(orient="records"))
    print(f"[Engine] Saved indicators for {len(merged)} sectors")

    # Print summary table
    summary = merged[["sector", "composite_score"]].sort_values(
        "composite_score", ascending=False
    )
    print("\n-- SME Health Score by Sector --")
    print(summary.to_string(index=False))
