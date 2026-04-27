"""
PDF parser — downloads filing PDFs and extracts:
  - Financial figures (revenue, EBITDA, PAT, debt) via table extraction
  - Keyword signals (order book, capex, credit stress, export, headcount)
"""

import hashlib
import re
import time
from pathlib import Path
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF
import requests

from config import PDF_CACHE_DIR, REQUEST_TIMEOUT, KEYWORDS, BATCH_SIZE
from storage.database import query, upsert_signals, upsert_financials

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

NUMBER_RE = re.compile(r"[\d,]+\.?\d*")


def _pdf_local_path(pdf_url: str) -> Path:
    name = hashlib.md5(pdf_url.encode()).hexdigest() + ".pdf"
    return PDF_CACHE_DIR / name


def download_pdf(pdf_url: str) -> Optional[Path]:
    if not pdf_url:
        return None
    dest = _pdf_local_path(pdf_url)
    if dest.exists():
        return dest
    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        if resp.status_code == 200 and "pdf" in resp.headers.get("Content-Type", "").lower():
            dest.write_bytes(resp.content)
            return dest
        print(f"[PDF] Non-PDF response for {pdf_url}: {resp.status_code}")
    except Exception as e:
        print(f"[PDF] Download failed for {pdf_url}: {e}")
    return None


def extract_text(pdf_path: Path) -> str:
    """Extract full text from PDF using PyMuPDF (faster than pdfplumber for text)."""
    try:
        doc = fitz.open(str(pdf_path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.lower()
    except Exception as e:
        print(f"[PDF] Text extraction failed for {pdf_path}: {e}")
        return ""


def extract_tables(pdf_path: Path) -> list[list]:
    """Extract tables from PDF using pdfplumber."""
    tables = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        print(f"[PDF] Table extraction failed for {pdf_path}: {e}")
    return tables


def _parse_number(raw: str) -> Optional[float]:
    if not raw:
        return None
    raw = raw.replace(",", "").strip()
    matches = NUMBER_RE.findall(raw)
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass
    return None


def _find_financial_in_tables(tables: list[list]) -> dict:
    """
    Heuristic: scan table rows for labels like 'Revenue', 'Total Income',
    'EBITDA', 'Profit After Tax', 'Total Debt' and extract adjacent numbers.
    """
    LABEL_MAP = {
        "revenue": ["total income", "revenue from operations", "net sales", "total revenue"],
        "ebitda": ["ebitda", "operating profit"],
        "pat": ["profit after tax", "pat", "net profit"],
        "total_debt": ["total debt", "total borrowings", "long term borrowing"],
    }

    result = {"revenue": None, "ebitda": None, "pat": None, "total_debt": None}

    for table in tables:
        for row in table:
            if not row:
                continue
            label_cell = str(row[0] or "").lower().strip()
            for key, patterns in LABEL_MAP.items():
                if result[key] is not None:
                    continue
                if any(p in label_cell for p in patterns):
                    # take the last non-empty numeric cell in the row
                    for cell in reversed(row[1:]):
                        val = _parse_number(str(cell or ""))
                        if val is not None:
                            result[key] = val
                            break
    return result


def scan_keywords(text: str) -> dict:
    """Return boolean flags for each keyword category."""
    return {
        category: any(kw in text for kw in kws)
        for category, kws in KEYWORDS.items()
    }


def parse_filing(filing_id: str, company_code: str, filing_date: str,
                 pdf_url: str, sector: str = "Unknown",
                 company_name: str = "", exchange: str = "") -> tuple[Optional[dict], Optional[dict]]:
    """Download and parse a single filing PDF.
    Returns (signals_record, financials_record) — either may be None."""
    local = download_pdf(pdf_url)
    if not local:
        return None, None

    text = extract_text(local)
    signals = scan_keywords(text)

    signal_record = {
        "id": filing_id,
        "filing_id": filing_id,
        "company_code": company_code,
        "filing_date": filing_date,
        "sector": sector,
        **signals,
        "raw_text": text[:5000],
    }

    tables = extract_tables(local)
    fin = _find_financial_in_tables(tables)
    fin_record = None
    if any(v is not None for v in fin.values()):
        fin_record = {
            "id": hashlib.md5(f"{filing_id}|{filing_date}".encode()).hexdigest(),
            "filing_id": filing_id,
            "company_code": company_code,
            "company_name": company_name,
            "exchange": exchange,
            "period_end": filing_date,
            "period_type": "Q",
            "sector": sector,
            **fin,
        }

    return signal_record, fin_record


def run():
    """Parse all unprocessed filings in raw_filings that have a pdf_url."""
    pending = query(f"""
        SELECT rf.id, rf.company_code, rf.company_name, rf.exchange,
               rf.filing_date, rf.pdf_url
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE rf.pdf_url IS NOT NULL
          AND rf.pdf_url != ''
          AND fs.filing_id IS NULL
        LIMIT {BATCH_SIZE}
    """)

    print(f"[PDF] Processing {len(pending)} unprocessed filings")
    signal_records = []
    fin_records = []

    for _, row in pending.iterrows():
        sig, fin = parse_filing(
            filing_id=row["id"],
            company_code=row["company_code"],
            filing_date=str(row["filing_date"]),
            pdf_url=row["pdf_url"],
            company_name=str(row.get("company_name", "") or ""),
            exchange=str(row.get("exchange", "") or ""),
        )
        if sig:
            signal_records.append(sig)
        if fin:
            fin_records.append(fin)
        time.sleep(0.1)

    if signal_records:
        upsert_signals(signal_records)
        print(f"[PDF] Saved signals for {len(signal_records)} filings")
    else:
        print("[PDF] No new signals to save")

    if fin_records:
        upsert_financials(fin_records)
        print(f"[PDF] Saved financials for {len(fin_records)} filings")
    else:
        print("[PDF] No financial tables found in PDFs")
