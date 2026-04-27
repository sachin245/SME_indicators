"""
BSE scraper — targets BSE SME Emerge segment and mainboard SME-sized companies.
Uses BSE's unofficial public JSON API endpoints with HTML fallback.
"""

import hashlib
import json
import time
from datetime import date, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import (
    BSE_API_BASE, BSE_BASE, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES,
    DEFAULT_DAYS_BACK, BSE_SME_SEGMENT,
)
from storage.database import upsert_filings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}


def _get(url: str, params: dict = None) -> Optional[dict | list]:
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 503):
                time.sleep(REQUEST_DELAY * (attempt + 2))
        except Exception as e:
            print(f"[BSE] Request error ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(REQUEST_DELAY)
    return None


def _filing_id(exchange: str, company_code: str, filing_date: str, headline: str) -> str:
    raw = f"{exchange}|{company_code}|{filing_date}|{headline}"
    return hashlib.md5(raw.encode()).hexdigest()


def _scrape_ann_get_data(str_cat: str, from_date: date, to_date: date, label: str) -> list[dict]:
    """Fetch filings from BSE AnnGetData endpoint with pagination."""
    url = f"{BSE_API_BASE}/AnnGetData/w"
    base_params = {
        "strCat": str_cat,
        "strPrevDate": from_date.strftime("%Y%m%d"),
        "strScrip": "",
        "strSearch": "P",
        "strToDate": to_date.strftime("%Y%m%d"),
        "strType": "C",
        "subcategory": "-1",
    }

    records = []
    page = 1
    while True:
        params = {**base_params, "pageno": page}
        data = _get(url, params)
        if not data:
            break

        items = data if isinstance(data, list) else data.get("Table", [])
        if not items:
            break

        for item in items:
            company_code = str(item.get("SCRIP_CD", "")).strip()
            company_name = str(item.get("SLONGNAME", "")).strip()
            filing_date_raw = str(item.get("NEWS_DT", "")).strip()[:10]
            headline = str(item.get("NEWSSUB", "")).strip()
            category = (item.get("CATEGORYNAME") or "").strip()
            pdf_url = ""
            attach = str(item.get("ATTACHMENTNAME", "")).strip()
            if attach:
                pdf_url = f"{BSE_BASE}/xml-data/corpfiling/AttachLive/{attach}"

            rec = {
                "id": _filing_id("BSE", company_code, filing_date_raw, headline),
                "exchange": "BSE",
                "company_code": company_code,
                "company_name": company_name,
                "filing_date": filing_date_raw or None,
                "category": category,
                "subcategory": "",
                "headline": headline,
                "pdf_url": pdf_url,
                "pdf_local": None,
                "raw_json": json.dumps(item),
                "scraped_at": None,
            }
            records.append(rec)

        total_pages = items[0].get("TotalPageCnt", 1) if items else 1
        if page >= total_pages:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    print(f"[BSE] Fetched {len(records)} {label} records")
    return records


def scrape_announcements(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch corporate announcements for BSE companies."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)
    print(f"[BSE] Scraping announcements from {from_date} to {to_date}")
    records = _scrape_ann_get_data("-1", from_date, to_date, "announcement")
    if not records:
        print("[BSE] No data from announcements API, falling back to HTML")
        return _scrape_announcements_html(from_date, to_date)
    return records


def _scrape_announcements_html(from_date: date, to_date: date) -> list[dict]:
    """HTML fallback for BSE announcements page."""
    url = f"{BSE_BASE}/corporates/ann.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        records = []
        for row in soup.select("table tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            company_name = cols[0].get_text(strip=True)
            headline = cols[2].get_text(strip=True)
            filing_date_raw = cols[3].get_text(strip=True)
            link_tag = cols[2].find("a")
            pdf_url = link_tag["href"] if link_tag and link_tag.get("href") else ""
            rec = {
                "id": _filing_id("BSE", company_name, filing_date_raw, headline),
                "exchange": "BSE",
                "company_code": company_name,
                "company_name": company_name,
                "filing_date": filing_date_raw or None,
                "category": "Announcement",
                "subcategory": "",
                "headline": headline,
                "pdf_url": pdf_url,
                "pdf_local": None,
                "raw_json": "{}",
                "scraped_at": None,
            }
            records.append(rec)
        print(f"[BSE] HTML fallback: {len(records)} records")
        return records
    except Exception as e:
        print(f"[BSE] HTML fallback failed: {e}")
        return []


def scrape_financial_results(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch financial result filings from BSE."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)
    print(f"[BSE] Scraping financial results from {from_date} to {to_date}")
    return _scrape_ann_get_data("Result", from_date, to_date, "financial result")


def run(days_back: int = DEFAULT_DAYS_BACK):
    """Main entry point — scrape and persist BSE filings."""
    records = []
    records += scrape_announcements(days_back)
    time.sleep(REQUEST_DELAY)
    records += scrape_financial_results(days_back)

    if records:
        upsert_filings(records)
        print(f"[BSE] Saved {len(records)} total records to DB")
    else:
        print("[BSE] No records to save")

    return records
