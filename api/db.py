import json
from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "sme_indicators.duckdb"


def execute_query(sql: str, params: list | None = None) -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute(sql, params or []).df()
        con.close()
        return json.loads(df.to_json(orient="records", date_format="iso"))
    except Exception as e:
        print(f"[DB] Query error: {e}")
        return []


def execute_count(sql: str, params: list | None = None) -> int:
    rows = execute_query(sql, params)
    return rows[0].get("total", 0) if rows else 0
