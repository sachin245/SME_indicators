import json
import re
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "sme_indicators.duckdb"

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _coerce_params(params: list | None) -> list:
    """DuckDB cannot compare DATE columns to VARCHAR parameters. Promote
    ISO YYYY-MM-DD strings to date objects so binding works transparently."""
    if not params:
        return []
    out = []
    for p in params:
        if isinstance(p, str) and _ISO_DATE_RE.match(p):
            try:
                out.append(datetime.strptime(p, "%Y-%m-%d").date())
                continue
            except ValueError:
                pass
        out.append(p)
    return out


def execute_query(sql: str, params: list | None = None) -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute(sql, _coerce_params(params)).df()
        con.close()
        return json.loads(df.to_json(orient="records", date_format="iso"))
    except Exception as e:
        print(f"[DB] Query error: {e}\n     SQL: {sql[:200]}\n     Params: {params}")
        return []


def execute_count(sql: str, params: list | None = None) -> int:
    rows = execute_query(sql, params)
    return rows[0].get("total", 0) if rows else 0
