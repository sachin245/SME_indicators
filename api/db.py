import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sme_indicators.db"


def _serialize(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def execute_query(sql: str, params: list | None = None) -> list[dict]:
    if not DB_PATH.exists():
        return []
    con = None
    try:
        con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params or [])
        return [{k: _serialize(row[k]) for k in row.keys()} for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB] Query error: {e}\n     SQL: {sql[:200]}\n     Params: {params}")
        return []
    finally:
        if con:
            con.close()


def execute_count(sql: str, params: list | None = None) -> int:
    rows = execute_query(sql, params)
    return rows[0].get("total", 0) if rows else 0
