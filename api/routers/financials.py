from typing import Optional, List
from fastapi import APIRouter, Query
from api.db import execute_query

router = APIRouter(tags=["financials"])


@router.get("/financials")
def get_financials(
    company_code: Optional[str] = None,
    sector: Optional[str] = None,
    exchange: Optional[List[str]] = Query(default=None),
    period_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 200,
):
    conditions = ["1=1"]
    params: list = []

    if company_code:
        conditions.append("company_code = ?")
        params.append(company_code)
    if sector:
        conditions.append("sector = ?")
        params.append(sector)
    if exchange:
        ph = ",".join("?" for _ in exchange)
        conditions.append(f"exchange IN ({ph})")
        params.extend(exchange)
    if period_type:
        conditions.append("period_type = ?")
        params.append(period_type)
    if from_date:
        conditions.append("period_end >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("period_end <= ?")
        params.append(to_date)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT company_code, company_name, exchange, sector,
               CAST(period_end AS VARCHAR) AS period_end, period_type,
               revenue, ebitda, pat, total_debt
        FROM financials
        WHERE {where}
        ORDER BY period_end DESC
        LIMIT ?
    """
    return execute_query(sql, params + [limit])
