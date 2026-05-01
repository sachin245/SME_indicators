"""
PDF parser — downloads filing PDFs and extracts signals and financials.

Two extraction modes:
  AI mode    (USE_AI_PARSER=true + OPENAI_API_KEY set):
               PyMuPDF for text → GPT-4o-mini for structured JSON extraction.
               Single pass, no pdfplumber needed.
  Regex mode (fallback):
               PyMuPDF for text → keyword scan, pdfplumber for table parsing.

Both modes run in parallel across PDF_WORKERS threads.
"""

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber
import requests

from config import (
    PDF_CACHE_DIR, REQUEST_TIMEOUT, KEYWORDS, BATCH_SIZE,
    OPENAI_API_KEY, PDF_WORKERS, USE_AI_PARSER,
)
from storage.database import query, upsert_signals, upsert_financials

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

NUMBER_RE = re.compile(r"[\d,]+\.?\d*")

# Initialise OpenAI client once at module load (the client is thread-safe)
_openai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[PDF] OpenAI client ready — AI extraction enabled")
    except ImportError:
        print("[PDF] openai package missing — falling back to regex extraction")


# ── Download ─────────────────────────────────────────────────────────────────

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
        print(f"[PDF] Non-PDF response ({resp.status_code}) for {pdf_url}")
    except Exception as e:
        print(f"[PDF] Download failed: {e}")
    return None


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> str:
    try:
        doc = fitz.open(str(pdf_path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.lower()
    except Exception as e:
        print(f"[PDF] Text extraction failed for {pdf_path}: {e}")
        return ""


# ── Regex / pdfplumber extraction (fallback) ─────────────────────────────────

def extract_tables(pdf_path: Path) -> list[list]:
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
    matches = NUMBER_RE.findall(raw.replace(",", "").strip())
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass
    return None


def _find_financial_in_tables(tables: list[list]) -> dict:
    LABEL_MAP = {
        "revenue": ["total income", "revenue from operations", "net sales", "total revenue"],
        "ebitda":  ["ebitda", "operating profit"],
        "pat":     ["profit after tax", "pat", "net profit"],
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
                    for cell in reversed(row[1:]):
                        val = _parse_number(str(cell or ""))
                        if val is not None:
                            result[key] = val
                            break
    return result


def scan_keywords(text: str) -> dict:
    return {
        category: any(kw in text for kw in kws)
        for category, kws in KEYWORDS.items()
    }


# ── AI extraction ─────────────────────────────────────────────────────────────

_AI_SYSTEM_PROMPT = """You are a financial analyst extracting structured data from Indian SME company filings.
Return ONLY a single valid JSON object — no explanation, no markdown.

Extract SIGNALS (boolean):
- order_book: order wins, new orders, order book growth, order inflow, order pipeline
- capex: capital expenditure, CAPEX, plant expansion, new facility, greenfield, brownfield
- credit_stress: NPA, non-performing asset, debt restructuring, default, insolvency, overdue, moratorium
- export: export revenue, forex, foreign currency, overseas sales, international revenue
- headcount: employee additions, hiring, workforce expansion, manpower

Extract FINANCIALS (numbers in INR crores; null if absent):
- revenue: Total Income / Revenue from Operations / Net Sales
- ebitda: EBITDA / Operating Profit
- pat: Profit After Tax / Net Profit / PAT
- total_debt: Total Debt / Total Borrowings

Example output:
{"order_book": false, "capex": true, "credit_stress": false, "export": false, "headcount": false, "revenue": 125.5, "ebitda": 18.2, "pat": 12.1, "total_debt": null}"""


def _ai_extract(text: str) -> dict:
    response = _openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _AI_SYSTEM_PROMPT},
            {"role": "user", "content": text[:4000]},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=150,
    )
    return json.loads(response.choices[0].message.content)


# ── Per-filing entry point ────────────────────────────────────────────────────

def parse_filing(
    filing_id: str,
    company_code: str,
    filing_date: str,
    pdf_url: str,
    sector: str = "Unknown",
    company_name: str = "",
    exchange: str = "",
) -> tuple[Optional[dict], Optional[dict]]:
    local = download_pdf(pdf_url)
    if not local:
        return None, None

    text = extract_text(local)

    signals: dict | None = None
    fin: dict | None = None

    if USE_AI_PARSER and _openai_client:
        try:
            extracted = _ai_extract(text)
            signals = {
                k: bool(extracted.get(k, False))
                for k in ("order_book", "capex", "credit_stress", "export", "headcount")
            }
            fin = {k: extracted.get(k) for k in ("revenue", "ebitda", "pat", "total_debt")}
        except Exception as e:
            print(f"[PDF] AI extraction failed for {filing_id}: {e} — using regex fallback")

    if signals is None:
        signals = scan_keywords(text)
        tables = extract_tables(local)
        fin = _find_financial_in_tables(tables)

    signal_record = {
        "id": filing_id,
        "filing_id": filing_id,
        "company_code": company_code,
        "filing_date": filing_date,
        "sector": sector,
        **signals,
        "raw_text": text[:5000],
    }

    fin_record = None
    if fin and any(v is not None for v in fin.values()):
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


# ── Batch runner ──────────────────────────────────────────────────────────────

def run():
    """Parse all unprocessed filings in parallel."""
    pending = query("""
        SELECT rf.id, rf.company_code, rf.company_name, rf.exchange,
               rf.filing_date, rf.pdf_url
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE rf.pdf_url IS NOT NULL
          AND rf.pdf_url != ''
          AND fs.filing_id IS NULL
        LIMIT ?
    """, [BATCH_SIZE])

    total = len(pending)
    mode = "AI (gpt-4o-mini)" if (USE_AI_PARSER and _openai_client) else "regex/pdfplumber"
    print(f"[PDF] {total} unprocessed filings — {PDF_WORKERS} workers — {mode} extraction")

    if total == 0:
        print("[PDF] Nothing to parse")
        return

    signal_records: list[dict] = []
    fin_records: list[dict] = []
    completed = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=PDF_WORKERS) as executor:
        futures = {
            executor.submit(
                parse_filing,
                filing_id=row["id"],
                company_code=row["company_code"],
                filing_date=str(row["filing_date"]),
                pdf_url=row["pdf_url"],
                company_name=str(row.get("company_name", "") or ""),
                exchange=str(row.get("exchange", "") or ""),
            ): row["id"]
            for _, row in pending.iterrows()
        }

        for future in as_completed(futures):
            completed += 1
            if completed % 25 == 0 or completed == total:
                print(f"[PDF]   {completed}/{total} done ({errors} errors)")
            try:
                sig, fin = future.result()
                if sig:
                    signal_records.append(sig)
                if fin:
                    fin_records.append(fin)
            except Exception as e:
                errors += 1
                print(f"[PDF] Worker error ({futures[future]}): {e}")

    if signal_records:
        upsert_signals(signal_records)
        print(f"[PDF] Saved {len(signal_records)} signal records")
    else:
        print("[PDF] No new signals")

    if fin_records:
        upsert_financials(fin_records)
        print(f"[PDF] Saved {len(fin_records)} financial records")
    else:
        print("[PDF] No financials extracted")
