from typing import Optional
from fastapi import APIRouter
from api.db import execute_query

router = APIRouter(tags=["indicators"])


@router.get("/sectors")
def list_sectors():
    return execute_query(
        "SELECT DISTINCT sector FROM indicators WHERE sector IS NOT NULL ORDER BY sector"
    )


@router.get("/indicators/latest")
def get_latest_indicators():
    sql = """
        SELECT i.*
        FROM indicators i
        INNER JOIN (
            SELECT sector, MAX(as_of_date) AS max_date
            FROM indicators
            GROUP BY sector
        ) latest ON i.sector = latest.sector AND i.as_of_date = latest.max_date
        ORDER BY i.composite_score DESC NULLS LAST
    """
    return execute_query(sql)


@router.get("/indicators")
def get_indicator_history(
    sector: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    conditions = ["1=1"]
    params: list = []

    if sector:
        conditions.append("sector = ?")
        params.append(sector)
    if from_date:
        conditions.append("as_of_date >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("as_of_date <= ?")
        params.append(to_date)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM indicators WHERE {where} ORDER BY sector, as_of_date"
    return execute_query(sql, params)
