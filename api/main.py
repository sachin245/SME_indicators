import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.db import execute_query
from api.routers import indicators, filings, financials, summary, pipeline

app = FastAPI(title="SME Indicators API", version="1.0.0")

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:4173",
]
_extra = [o.strip() for o in os.getenv("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS + _extra,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(indicators.router, prefix="/api")
app.include_router(filings.router, prefix="/api")
app.include_router(financials.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/data")
def data_health():
    """Freshness and coverage snapshot — used by the dashboard to warn on
    stale or unclassified data."""
    rows = execute_query("""
        SELECT
            (SELECT COUNT(*) FROM raw_filings)                                AS total_filings,
            (SELECT COUNT(*) FROM filing_signals)                             AS pdf_parsed,
            (SELECT COUNT(*) FROM financials)                                 AS xbrl_parsed,
            (SELECT COUNT(*) FROM indicators)                                 AS indicator_rows,
            (SELECT CAST(MAX(filing_date) AS VARCHAR) FROM raw_filings)       AS latest_filing,
            (SELECT CAST(MIN(filing_date) AS VARCHAR) FROM raw_filings)       AS earliest_filing,
            (SELECT CAST(MAX(scraped_at)  AS VARCHAR) FROM raw_filings)       AS last_scrape,
            (SELECT CAST(MAX(computed_at) AS VARCHAR) FROM indicators)        AS last_compute,
            (SELECT COUNT(DISTINCT sector) FROM filing_signals
                WHERE sector IS NOT NULL AND sector <> 'Unknown')             AS classified_sectors,
            (SELECT COUNT(*) FROM filing_signals
                WHERE sector IS NULL OR sector = 'Unknown')                   AS unclassified_signals
    """)
    snapshot = rows[0] if rows else {}
    total = snapshot.get("total_filings") or 0
    parsed = snapshot.get("pdf_parsed") or 0
    snapshot["pdf_parse_coverage_pct"] = round(parsed / total * 100, 2) if total else 0
    snapshot["status"] = "ok" if total and parsed and snapshot.get("classified_sectors", 0) > 1 \
                                else "degraded"
    return snapshot


# Serve React SPA — must be last so API routes take precedence
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
