import json
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
    # Serve from dashboard_cache when available — updated at end of each pipeline run
    cache = execute_query(
        "SELECT value_json FROM dashboard_cache WHERE key = 'latest_indicators'"
    )
    if cache and cache[0].get("value_json"):
        return json.loads(cache[0]["value_json"])

    # Fall back to live query using a window function (single pass, no self-join)
    sql = """
        SELECT id, sector, as_of_date,
               revenue_momentum, margin_pressure, order_book_signal,
               credit_stress, capex_intentions, export_outlook,
               composite_score, computed_at
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY sector ORDER BY as_of_date DESC
                   ) AS rn
            FROM indicators
        )
        WHERE rn = 1
        ORDER BY composite_score DESC NULLS LAST
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
