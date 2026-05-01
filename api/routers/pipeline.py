"""
Admin-only pipeline routes.

These endpoints mutate state (run scrapers, write to the DB) and are intended
to be called from the Streamlit admin console (`dashboard/app.py`) when it is
configured against a remote API via ``SME_ADMIN_API_URL``. The React viewer
does NOT call these routes — it is read-only.

If/when this service grows multi-user, gate these behind auth.
"""

import threading
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

import config

router = APIRouter(tags=["pipeline (admin)"])

_state: dict = {"status": "idle", "message": "", "started_at": None}
_lock = threading.Lock()


def _run():
    try:
        import sys, io, time
        # Windows stdout may use cp1252; force UTF-8 so scrapers can print freely
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        from storage.database import init_db
        from scrapers import bse_scraper, nse_scraper

        _state["message"] = "Scraping BSE filings…"
        init_db()
        bse_scraper.run(days_back=90)

        time.sleep(2)

        _state["message"] = "Scraping NSE filings…"
        nse_scraper.run(days_back=90)

        _state["message"] = "Parsing filings…"
        from parsers import pdf_parser, xbrl_parser
        pdf_parser.run()
        xbrl_parser.run()

        _state["message"] = "Computing indicators…"
        from indicators.engine import run as engine_run
        engine_run()

        _state["status"] = "idle"
        _state["message"] = f"Done — last run {datetime.now().strftime('%H:%M:%S')}"

    except Exception as exc:
        _state["status"] = "error"
        _state["message"] = str(exc)


class RunRequest(BaseModel):
    use_ai_parser: bool | None = None  # None = leave config flag untouched


@router.post("/pipeline/run")
def trigger_pipeline(req: RunRequest | None = None):
    with _lock:
        if _state["status"] == "running":
            return {"ok": False, "message": "Pipeline already running"}
        if req is not None and req.use_ai_parser is not None:
            config.USE_AI_PARSER = bool(req.use_ai_parser)
        _state["status"] = "running"
        _state["started_at"] = datetime.now().isoformat()
        mode = "AI" if config.USE_AI_PARSER else "regex"
        _state["message"] = f"Starting… (parser: {mode})"
        threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": _state["message"]}


@router.get("/pipeline/status")
def get_status():
    return {**_state, "use_ai_parser": bool(getattr(config, "USE_AI_PARSER", True))}


@router.post("/pipeline/parser-mode")
def set_parser_mode(req: RunRequest):
    """Toggle the AI parser flag without starting a run."""
    if req.use_ai_parser is None:
        return {"ok": False, "message": "use_ai_parser is required"}
    config.USE_AI_PARSER = bool(req.use_ai_parser)
    return {"ok": True, "use_ai_parser": config.USE_AI_PARSER}
