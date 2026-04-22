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


def scrape_announcements(days_back: int = DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch corporate announcements for BSE SME Emerge companies."""
    to_date = date.today()
    from_date = to_date - timedelta(days=days_back)

    print(f"[BSE] Scraping announcements from {from_date} to {to_date}")

    records = []
    # BSE announcement API — segment=BE targets SME Emerge
    url = f"{BSE_API_BASE}/AnnSubCategoryGetData/w"
    params = {
        "strCat": "-1",
        "strPrevDate": from_date.strftime("%Y%m%d"),
        "strScrip": "",
        "strSearch": "P",
        "strToDate": to_date.strftime("%Y%m%d"),
        "strType": "C",
        "subcategory": "-1",
    }

    data = _get(url, params)
    if not data:
        print("[BSE] No data returned from announcements API, falling back to HTML")
        return _scrape_announcements_html(from_date, to_date)

    items = data if isinstance(data, list) else data.get("Table", [])
    for item in items:
        company_code = str(item.get("SCRIP_CD", "")).strip()
        company_name = str(item.get("SLONGNAME", "")).strip()
        filing_date_raw = str(item.get("NEWS_DT", "")).strip()[:10]
        headline = str(item.get("NEWSSUB", "")).strip()
        category = str(item.get("CATEGORYNAME", "")).strip()
        subcategory = str(item.get("SUBCATNAME", "")).strip()
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
            "subcategory": subcategory,
            "headline": headline,
            "pdf_url": pdf_url,
            "pdf_local": None,
            "raw_json": json.dumps(item),
            "scraped_at": None,
        }
        records.append(rec)
        time.sleep(0.05)

    print(f"[BSE] Fetched {len(records)} announcement records")
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

    url = f"{BSE_API_BASE}/getFinancialResults/w"
    params = {
        "Fyear": "",
        "Qtype": "quartly",
        "scripcode": "",
        "segment": "",
        "strSearch": "P",
    }

    data = _get(url, params)
    records = []
    items = []
    if data:
        items = data if isinstance(data, list) else data.get("Table", [])

    for item in items:
        company_code = str(item.get("SCRIPCODE", "")).strip()
        company_name = str(item.get("SCRIP_NAME", "")).strip()
        filing_date_raw = str(item.get("SUBMISSION_DATE", "")).strip()[:10]
        headline = f"Financial Results - {item.get('PERIOD', '')}"
        pdf_url = ""
        attach = str(item.get("FILENAME", "")).strip()
        if attach:
            pdf_url = f"{BSE_BASE}/xml-data/corpfiling/AttachLive/{attach}"

        rec = {
            "id": _filing_id("BSE", company_code, filing_date_raw, headline),
            "exchange": "BSE",
            "company_code": company_code,
            "company_name": company_name,
            "filing_date": filing_date_raw or None,
            "category": "Results",
            "subcategory": item.get("PERIOD", ""),
            "headline": headline,
            "pdf_url": pdf_url,
            "pdf_local": None,
            "raw_json": json.dumps(item),
            "scraped_at": None,
        }
        records.append(rec)
        time.sleep(0.05)

    print(f"[BSE] Fetched {len(records)} financial result records")
    return records


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
