import os
from datetime import date, datetime

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sme:sme@localhost:5432/sme_indicators")


def _serialize(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def execute_query(sql: str, params: list | None = None) -> list[dict]:
    con = None
    try:
        con = psycopg2.connect(DATABASE_URL)
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [{k: _serialize(v) for k, v in row.items()} for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB] Query error: {e}\n     SQL: {sql[:200]}\n     Params: {params}")
        return []
    finally:
        if con:
            con.close()


def execute_count(sql: str, params: list | None = None) -> int:
    rows = execute_query(sql, params)
    return rows[0].get("total", 0) if rows else 0
