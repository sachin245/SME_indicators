import threading
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["pipeline"])

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


@router.post("/pipeline/run")
def trigger_pipeline():
    with _lock:
        if _state["status"] == "running":
            return {"ok": False, "message": "Pipeline already running"}
        _state["status"] = "running"
        _state["started_at"] = datetime.now().isoformat()
        _state["message"] = "Starting…"
        threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": "Pipeline started"}


@router.get("/pipeline/status")
def get_status():
    return _state
