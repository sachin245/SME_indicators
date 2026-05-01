import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sme_indicators.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "con") or _local.con is None:
        con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA cache_size=-64000")    # 64 MB page cache
        con.execute("PRAGMA temp_store=MEMORY")    # sort/group in RAM
        con.execute("PRAGMA mmap_size=268435456")  # 256 MB memory-mapped I/O
        _local.con = con
    return _local.con


def _serialize(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def execute_query(sql: str, params: list | None = None) -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        con = _get_conn()
        cur = con.execute(sql, params or [])
        return [{k: _serialize(row[k]) for k in row.keys()} for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB] Query error: {e}\n     SQL: {sql[:200]}\n     Params: {params}")
        _local.con = None  # reset on error so next call gets a fresh connection
        return []


def execute_count(sql: str, params: list | None = None) -> int:
    rows = execute_query(sql, params)
    return rows[0].get("total", 0) if rows else 0
