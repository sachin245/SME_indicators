from typing import Optional, List
from fastapi import APIRouter, Query
from api.db import execute_query, execute_count

router = APIRouter(tags=["filings"])

SIGNAL_COLS = ["order_book", "capex", "credit_stress", "export", "headcount"]


def _build_filings_where(
    exchange: Optional[List[str]],
    sector: Optional[str],
    company_code: Optional[str],
    category: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    signals: Optional[List[str]],
) -> tuple[str, list]:
    conditions = ["1=1"]
    params: list = []

    if exchange:
        ph = ",".join("?" for _ in exchange)
        conditions.append(f"rf.exchange IN ({ph})")
        params.extend(exchange)
    if sector:
        conditions.append("COALESCE(fs.sector, 'Unknown') = ?")
        params.append(sector)
    if company_code:
        conditions.append("rf.company_code = ?")
        params.append(company_code)
    if category:
        conditions.append("rf.category = ?")
        params.append(category)
    if from_date:
        conditions.append("rf.filing_date >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("rf.filing_date <= ?")
        params.append(to_date)
    if signals:
        valid = [s for s in signals if s in SIGNAL_COLS]
        if valid:
            sig_conds = " OR ".join(f"COALESCE(fs.{s}, false) = true" for s in valid)
            conditions.append(f"({sig_conds})")

    return " AND ".join(conditions), params


@router.get("/filings")
def get_filings(
    exchange: Optional[List[str]] = Query(default=None),
    sector: Optional[str] = None,
    company_code: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    signals: Optional[List[str]] = Query(default=None),
    page: int = 0,
    page_size: int = 50,
):
    where, params = _build_filings_where(
        exchange, sector, company_code, category, from_date, to_date, signals
    )

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE {where}
    """
    total = execute_count(count_sql, params)

    data_sql = f"""
        SELECT rf.id, rf.exchange, rf.company_code, rf.company_name,
               CAST(rf.filing_date AS VARCHAR) AS filing_date,
               rf.category, rf.subcategory, rf.headline, rf.pdf_url,
               COALESCE(fs.order_book, false)   AS order_book,
               COALESCE(fs.capex, false)         AS capex,
               COALESCE(fs.credit_stress, false) AS credit_stress,
               COALESCE(fs.export, false)        AS export,
               COALESCE(fs.headcount, false)     AS headcount,
               COALESCE(fs.sector, 'Unknown')    AS sector
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE {where}
        ORDER BY rf.filing_date DESC
        LIMIT ? OFFSET ?
    """
    data = execute_query(data_sql, params + [page_size, page * page_size])

    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/filings/categories")
def list_categories():
    return execute_query(
        "SELECT DISTINCT category FROM raw_filings WHERE category IS NOT NULL ORDER BY category"
    )


@router.get("/companies")
def list_companies(
    exchange: Optional[List[str]] = Query(default=None),
    sector: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 0,
    page_size: int = 50,
):
    conditions = ["1=1"]
    params: list = []

    if exchange:
        ph = ",".join("?" for _ in exchange)
        conditions.append(f"rf.exchange IN ({ph})")
        params.extend(exchange)
    if sector:
        conditions.append("COALESCE(fs.sector, 'Unknown') = ?")
        params.append(sector)
    if search:
        conditions.append(
            "(LOWER(rf.company_name) LIKE ? OR LOWER(rf.company_code) LIKE ?)"
        )
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])

    where = " AND ".join(conditions)

    count_sql = f"""
        SELECT COUNT(DISTINCT rf.company_code || '|' || rf.exchange) AS total
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE {where}
    """
    total = execute_count(count_sql, params)

    data_sql = f"""
        SELECT rf.company_code,
               ANY_VALUE(rf.company_name) AS company_name,
               rf.exchange,
               ANY_VALUE(COALESCE(fs.sector, 'Unknown')) AS sector,
               COUNT(rf.id) AS filing_count
        FROM raw_filings rf
        LEFT JOIN filing_signals fs ON rf.id = fs.filing_id
        WHERE {where}
        GROUP BY rf.company_code, rf.exchange
        ORDER BY rf.company_code
        LIMIT ? OFFSET ?
    """
    data = execute_query(data_sql, params + [page_size, page * page_size])

    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/signals/trend")
def get_signal_trend(
    sector: Optional[str] = None,
    exchange: Optional[List[str]] = Query(default=None),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    bucket: str = "month",
):
    if bucket not in ("week", "month"):
        bucket = "month"

    conditions = ["1=1"]
    params: list = []

    if sector:
        conditions.append("fs.sector = ?")
        params.append(sector)
    if exchange:
        ph = ",".join("?" for _ in exchange)
        conditions.append(f"rf.exchange IN ({ph})")
        params.extend(exchange)
    if from_date:
        conditions.append("fs.filing_date >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("fs.filing_date <= ?")
        params.append(to_date)

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            CAST(DATE_TRUNC('{bucket}', fs.filing_date) AS VARCHAR) AS bucket,
            COUNT(*) AS total,
            SUM(CAST(fs.order_book AS INTEGER))    AS order_book_hits,
            SUM(CAST(fs.capex AS INTEGER))         AS capex_hits,
            SUM(CAST(fs.credit_stress AS INTEGER)) AS credit_stress_hits,
            SUM(CAST(fs.export AS INTEGER))        AS export_hits,
            SUM(CAST(fs.headcount AS INTEGER))     AS headcount_hits
        FROM filing_signals fs
        LEFT JOIN raw_filings rf ON fs.filing_id = rf.id
        WHERE {where}
        GROUP BY DATE_TRUNC('{bucket}', fs.filing_date)
        ORDER BY bucket
    """

    rows = execute_query(sql, params)
    for r in rows:
        total = r.get("total") or 1
        r["order_book_rate"] = round((r.pop("order_book_hits") or 0) / total * 100, 1)
        r["capex_rate"] = round((r.pop("capex_hits") or 0) / total * 100, 1)
        r["credit_stress_rate"] = round((r.pop("credit_stress_hits") or 0) / total * 100, 1)
        r["export_rate"] = round((r.pop("export_hits") or 0) / total * 100, 1)
        r["headcount_rate"] = round((r.pop("headcount_hits") or 0) / total * 100, 1)
    return rows
