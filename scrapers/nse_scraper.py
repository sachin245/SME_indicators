"""
NSE scraper — targets NSE Emerge (SME platform) and SME-sized NSE-listed companies.
NSE uses aggressive bot detection; we establish a browser session via Playwright,
then reuse the session cookies for subsequent API calls.

Cookie caching: cookies are persisted to NSE_COOKIE_FILE (data/nse_cookies.json)
and reused across runs.  A new browser session is only launched when the cache is
absent, older than 4 hours, or when NSE returns 401.
"""

import hashlib
import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import requests

from config import (
    NSE_API_BASE, NSE_BASE, NSE_COOKIE_FILE,
    REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES,
    DEFAULT_DAYS_BACK,
)
from storage.database import upsert_filings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nseindia.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

_COOKIE_TTL = 4 * 3600  # seconds before we re-launch the browser


# ── Cookie cache ─────────────────────────────────────────────────────────────

def _load_cached_cookies() -> dict:
    try:
        if NSE_COOKIE_FILE.exists():
            data = json.loads(NSE_COOKIE_FILE.read_text())
            if time.time() - data.get("timestamp", 0) < _COOKIE_TTL:
                print("[NSE] Using cached session cookies")
                return data["cookies"]
    except Exception:
        pass
    return {}


def _save_cookies(cookies: dict):
    try:
        NSE_COOKIE_FILE.write_text(
            json.dumps({"cookies": cookies, "timestamp": time.time()})
        )
    except Exception as e:
        print(f"[NSE] Could not save cookie cache: {e}")


def _launch_browser_session() -> dict:
    """Launch headless Chrome via Playwright to get fresh NSE session cookies."""
    print("[NSE] Launching browser to establish session cookies...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()
            page.goto(NSE_BASE, timeout=60000)
            page.wait_for_timeout(3000)
            cookies = {c["name"]: c["value"] for c in context.cookies()}
            browser.close()
        _save_cookies(cookies)
        print("[NSE] Browser session established and cookies cached")
        return cookies
    except Exception as e:
        print(f"[NSE] Playwright session failed: {e}")
        return {}


def _get_session_cookies(force_refresh: bool = False) -> dict:
    if not force_refresh:
        cached = _load_cached_cookies()
        if cached:
            return cached
    return _launch_browser_session()


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str, params: dict = None, cookies: dict = None) -> Optional[dict | list]:
    _cookies = cookies if cookies is not None else _get_session_cookies()
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                url, params=params, headers=HEADERS,
                cookies=_cookies, timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 401:
                print("[NSE] Session expired — refreshing cookies")
                _cookies = _get_session_cookies(force_refresh=True)
            elif resp.status_code in (429, 503):
                time.sleep(REQUEST_DELAY * (attempt + 2))
        except Exception as e:
            print(f"[NSE] Request error ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(REQUEST_DELAY)
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _filing_id(exchange: str, company_code: str, filing_date: str, headline: str) -> str:
    return hashlib.md5(f"{exchange}|{company_code}|{filing_date}|{headline}".encode()).hexdigest()


# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_announcements(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    print(f"[NSE] Scraping announcements from {from_date} to {to_date}")
    cookies = _get_session_cookies()

    records = []
    page_num = 1
    while True:
        params = {
            "index": "equities",
            "from_date": from_date.strftime("%d-%m-%Y"),
            "to_date": to_date.strftime("%d-%m-%Y"),
            "category": "announcement",
            "symbol": "",
            "pagenum": page_num,
        }
        data = _get(f"{NSE_API_BASE}/corp-announcements", params=params, cookies=cookies)
        if not data:
            break

        items = data if isinstance(data, list) else data.get("data", [])
        if not items:
            break

        for item in items:
            company_code = str(item.get("symbol", "")).strip()
            company_name = str(item.get("sm_name", "")).strip()
            filing_date_raw = str(item.get("an_dt", "")).strip()[:10]
            headline = str(item.get("desc", "")).strip()
            category = str(item.get("attchmntType", "")).strip()
            pdf_url = ""
            attach = str(item.get("attchmntFile", "")).strip()
            if attach:
                pdf_url = f"{NSE_BASE}/corporate-announcements/attachment/{attach}"

            records.append({
                "id": _filing_id("NSE", company_code, filing_date_raw, headline),
                "exchange": "NSE",
                "company_code": company_code,
                "company_name": company_name,
                "filing_date": filing_date_raw or None,
                "category": category or "Announcement",
                "subcategory": str(item.get("sort_date", "")).strip(),
                "headline": headline,
                "pdf_url": pdf_url,
                "pdf_local": None,
                "raw_json": json.dumps(item),
                "scraped_at": None,
            })

        time.sleep(REQUEST_DELAY)
        page_num += 1
        if len(items) < 20:
            break

    print(f"[NSE] Fetched {len(records)} announcement records")
    return records


def scrape_financial_results(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    print(f"[NSE] Scraping financial results from {from_date} to {to_date}")
    cookies = _get_session_cookies()

    params = {
        "index": "equities",
        "from_date": from_date.strftime("%d-%m-%Y"),
        "to_date": to_date.strftime("%d-%m-%Y"),
        "category": "financials",
    }
    data = _get(f"{NSE_API_BASE}/corp-announcements", params=params, cookies=cookies)

    records = []
    items = (data if isinstance(data, list) else data.get("data", [])) if data else []

    for item in items:
        company_code = str(item.get("symbol", "")).strip()
        company_name = str(item.get("sm_name", "")).strip()
        filing_date_raw = str(item.get("an_dt", "")).strip()[:10]
        period = str(item.get("period", "")).strip()
        headline = f"Financial Results - {period}" if period else "Financial Results"
        pdf_url = ""
        attach = str(item.get("attchmntFile", "")).strip()
        if attach:
            pdf_url = f"{NSE_BASE}/corporate-announcements/attachment/{attach}"

        records.append({
            "id": _filing_id("NSE", company_code, filing_date_raw, headline),
            "exchange": "NSE",
            "company_code": company_code,
            "company_name": company_name,
            "filing_date": filing_date_raw or None,
            "category": "Results",
            "subcategory": period,
            "headline": headline,
            "pdf_url": pdf_url,
            "pdf_local": None,
            "raw_json": json.dumps(item),
            "scraped_at": None,
        })

    print(f"[NSE] Fetched {len(records)} financial result records")
    return records


def run(days_back: int = DEFAULT_DAYS_BACK):
    records = []
    records += scrape_announcements(days_back)
    time.sleep(REQUEST_DELAY)
    records += scrape_financial_results(days_back)

    if records:
        upsert_filings(records)
        print(f"[NSE] Saved {len(records)} total records to DB")
    else:
        print("[NSE] No records to save")

    return records
