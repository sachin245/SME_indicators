from typing import Optional, List
from fastapi import APIRouter, Query
from api.db import execute_query, execute_count

router = APIRouter(tags=["summary"])


@router.get("/summary")
def get_summary(
    exchange: Optional[List[str]] = Query(default=None),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    rf_conditions = ["1=1"]
    rf_params: list = []

    if exchange:
        ph = ",".join("?" for _ in exchange)
        rf_conditions.append(f"exchange IN ({ph})")
        rf_params.extend(exchange)
    if from_date:
        rf_conditions.append("filing_date >= ?")
        rf_params.append(from_date)
    if to_date:
        rf_conditions.append("filing_date <= ?")
        rf_params.append(to_date)

    rf_where = " AND ".join(rf_conditions)

    counts_row = execute_query(
        f"""
        SELECT COUNT(*) AS total_filings,
               COUNT(DISTINCT company_code) AS total_companies
        FROM raw_filings
        WHERE {rf_where}
        """,
        rf_params,
    )
    total_filings = counts_row[0].get("total_filings", 0) if counts_row else 0
    total_companies = counts_row[0].get("total_companies", 0) if counts_row else 0

    # Signal counts (join for exchange filter)
    sig_conditions = ["1=1"]
    sig_params: list = []
    if exchange:
        ph = ",".join("?" for _ in exchange)
        sig_conditions.append(f"rf.exchange IN ({ph})")
        sig_params.extend(exchange)
    if from_date:
        sig_conditions.append("fs.filing_date >= ?")
        sig_params.append(from_date)
    if to_date:
        sig_conditions.append("fs.filing_date <= ?")
        sig_params.append(to_date)

    sig_where = " AND ".join(sig_conditions)
    signal_rows = execute_query(
        f"""
        SELECT
            COALESCE(SUM(CAST(fs.order_book AS INTEGER)), 0)    AS order_book,
            COALESCE(SUM(CAST(fs.capex AS INTEGER)), 0)         AS capex,
            COALESCE(SUM(CAST(fs.credit_stress AS INTEGER)), 0) AS credit_stress,
            COALESCE(SUM(CAST(fs.export AS INTEGER)), 0)        AS export,
            COALESCE(SUM(CAST(fs.headcount AS INTEGER)), 0)     AS headcount
        FROM filing_signals fs
        LEFT JOIN raw_filings rf ON fs.filing_id = rf.id
        WHERE {sig_where}
        """,
        sig_params,
    )

    composite_rows = execute_query(
        """
        SELECT AVG(composite_score) AS score
        FROM indicators
        WHERE as_of_date = (SELECT MAX(as_of_date) FROM indicators)
        """
    )

    return {
        "total_filings": total_filings,
        "total_companies": total_companies,
        "composite_score": round((composite_rows[0].get("score") or 0), 1) if composite_rows else 0,
        "signal_counts": signal_rows[0] if signal_rows else {
            "order_book": 0, "capex": 0, "credit_stress": 0, "export": 0, "headcount": 0
        },
    }
