"""
XBRL parser — parses MCA-mandated XBRL financial data from BSE/NSE filings.
Uses lxml to extract structured financials without an external XBRL library.
"""

import hashlib
import re
from io import BytesIO
from typing import Optional

import requests
from lxml import etree

from config import REQUEST_TIMEOUT
from storage.database import upsert_financials

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Common XBRL namespace prefixes used in Indian filings
NS_PATTERNS = [
    "in-bse-fin",
    "in-nse-fin",
    "in-gaap",
    "ifrs-full",
]

# Tag local-name patterns → financial field mapping
FIELD_PATTERNS = {
    "revenue": [
        "Revenue", "RevenueFromOperations", "TotalRevenue",
        "NetSales", "TotalIncome", "SalesAndOtherIncome",
    ],
    "ebitda": [
        "EarningsBeforeInterestTaxDepreciationAndAmortization",
        "EBITDA", "OperatingProfit",
    ],
    "pat": [
        "ProfitAfterTax", "ProfitLossForPeriod", "NetProfit",
        "ProfitLossAfterTax",
    ],
    "total_debt": [
        "TotalBorrowings", "LongTermBorrowings", "TotalDebt",
        "BorrowingsTotal",
    ],
}


def _fetch_xbrl(url: str) -> Optional[bytes]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            ct = resp.headers.get("Content-Type", "")
            if "xml" in ct or url.endswith(".xml") or url.endswith(".xbrl"):
                return resp.content
    except Exception as e:
        print(f"[XBRL] Fetch failed for {url}: {e}")
    return None


def _local_name(tag: str) -> str:
    """Strip namespace URI from tag like {http://...}TagName → TagName."""
    return re.sub(r"\{.*?\}", "", tag)


def _parse_value(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_xbrl_bytes(content: bytes) -> dict:
    """Parse XBRL XML bytes and return a dict with financial fields."""
    result = {f: None for f in FIELD_PATTERNS}
    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError as e:
        print(f"[XBRL] XML parse error: {e}")
        return result

    for elem in root.iter():
        local = _local_name(elem.tag)
        for field, patterns in FIELD_PATTERNS.items():
            if result[field] is not None:
                continue
            if any(p.lower() in local.lower() for p in patterns):
                val = _parse_value(elem.text)
                if val is not None:
                    result[field] = val
                    break

    return result


def _filing_fin_id(filing_id: str, period: str) -> str:
    raw = f"{filing_id}|{period}"
    return hashlib.md5(raw.encode()).hexdigest()


def parse_filing(filing_id: str, company_code: str, company_name: str,
                 exchange: str, xbrl_url: str, period_end: str,
                 period_type: str = "Q", sector: str = "Unknown") -> Optional[dict]:
    """Download and parse XBRL for a single filing."""
    content = _fetch_xbrl(xbrl_url)
    if not content:
        return None

    financials = parse_xbrl_bytes(content)
    if all(v is None for v in financials.values()):
        print(f"[XBRL] No financial data found for {company_code} / {filing_id}")
        return None

    return {
        "id": _filing_fin_id(filing_id, period_end),
        "filing_id": filing_id,
        "company_code": company_code,
        "company_name": company_name,
        "exchange": exchange,
        "period_end": period_end,
        "period_type": period_type,
        "sector": sector,
        **financials,
    }


def _xbrl_url_from_pdf_url(pdf_url: str) -> str:
    """
    BSE/NSE often host XBRL alongside PDF with same base name.
    Attempt to derive XBRL URL from PDF URL.
    """
    if not pdf_url:
        return ""
    return pdf_url.replace(".pdf", ".xml").replace(".PDF", ".xml")


def run():
    """Parse XBRL for all Results filings not yet in financials table."""
    from storage.database import query

    pending = query("""
        SELECT rf.id, rf.company_code, rf.company_name, rf.exchange,
               rf.pdf_url, rf.filing_date, rf.subcategory
        FROM raw_filings rf
        LEFT JOIN financials f ON rf.id = f.filing_id
        WHERE rf.category = 'Results'
          AND rf.pdf_url IS NOT NULL
          AND rf.pdf_url != ''
          AND f.filing_id IS NULL
        LIMIT 200
    """)

    print(f"[XBRL] Processing {len(pending)} result filings")
    records = []

    for _, row in pending.iterrows():
        xbrl_url = _xbrl_url_from_pdf_url(row["pdf_url"])
        rec = parse_filing(
            filing_id=row["id"],
            company_code=row["company_code"],
            company_name=str(row.get("company_name", "")),
            exchange=row["exchange"],
            xbrl_url=xbrl_url,
            period_end=str(row["filing_date"]),
            period_type="Q" if "quarter" in str(row.get("subcategory", "")).lower() else "A",
        )
        if rec:
            records.append(rec)

    if records:
        upsert_financials(records)
        print(f"[XBRL] Saved financials for {len(records)} filings")
    else:
        print("[XBRL] No new financials to save")
