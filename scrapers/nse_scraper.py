"""
NSE scraper — targets NSE Emerge (SME platform) and SME-sized NSE-listed companies.
NSE uses aggressive bot detection; we establish a browser session via Playwright,
then reuse the session cookies for subsequent requests API calls.
"""

import hashlib
import json
import time
from datetime import date, timedelta
from typing import Optional

import requests

from config import (
    NSE_API_BASE, NSE_BASE, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES,
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


def _get_session_cookies() -> dict:
    """Use Playwright to load NSE homepage and extract session cookies."""
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
            page.wait_for_timeout(3000)  # let JS load
            cookies = {c["name"]: c["value"] for c in context.cookies()}
            browser.close()
            return cookies
    except Exception as e:
        print(f"[NSE] Playwright session failed: {e}")
        return {}


def _get(url: str, params: dict = None, cookies: dict = None) -> Optional[dict | list]:
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                url, params=params, headers=HEADERS,
                cookies=cookies or {}, timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 503):
                time.sleep(REQUEST_DELAY * (attempt + 2))
            elif resp.status_code == 401:
                print("[NSE] Session expired — refreshing cookies")
                cookies = _get_session_cookies()
        except Exception as e:
            print(f"[NSE] Request error ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(REQUEST_DELAY)
    return None


def _filing_id(exchange: str, company_code: str, filing_date: str, headline: str) -> str:
    raw = f"{exchange}|{company_code}|{filing_date}|{headline}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_announcements(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch corporate announcements from NSE."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    print(f"[NSE] Scraping announcements from {from_date} to {to_date}")
    print("[NSE] Establishing browser session for cookies...")
    cookies = _get_session_cookies()
    time.sleep(REQUEST_DELAY)

    records = []
    # NSE paginates — iterate pages until data exhausted
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

            rec = {
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
            }
            records.append(rec)

        time.sleep(REQUEST_DELAY)
        page_num += 1
        if len(items) < 20:  # last page
            break

    print(f"[NSE] Fetched {len(records)} announcement records")
    return records


def scrape_financial_results(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch financial result filings from NSE."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    print(f"[NSE] Scraping financial results from {from_date} to {to_date}")
    cookies = _get_session_cookies()
    time.sleep(REQUEST_DELAY)

    params = {
        "index": "equities",
        "from_date": from_date.strftime("%d-%m-%Y"),
        "to_date": to_date.strftime("%d-%m-%Y"),
        "category": "financials",
    }
    data = _get(f"{NSE_API_BASE}/corp-announcements", params=params, cookies=cookies)

    records = []
    items = []
    if data:
        items = data if isinstance(data, list) else data.get("data", [])

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

        rec = {
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
        }
        records.append(rec)
        time.sleep(0.05)

    print(f"[NSE] Fetched {len(records)} financial result records")
    return records


def run(days_back: int = DEFAULT_DAYS_BACK):
    """Main entry point — scrape and persist NSE filings."""
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
