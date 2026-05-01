import sqlite3
import pandas as pd
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db():
    con = get_connection()
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS raw_filings (
                id            TEXT PRIMARY KEY,
                exchange      TEXT NOT NULL,
                company_code  TEXT NOT NULL,
                company_name  TEXT,
                filing_date   TEXT,
                category      TEXT,
                subcategory   TEXT,
                headline      TEXT,
                pdf_url       TEXT,
                pdf_local     TEXT,
                raw_json      TEXT,
                scraped_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS financials (
                id            TEXT PRIMARY KEY,
                filing_id     TEXT,
                company_code  TEXT NOT NULL,
                company_name  TEXT,
                exchange      TEXT,
                period_end    TEXT,
                period_type   TEXT,
                revenue       REAL,
                ebitda        REAL,
                pat           REAL,
                total_debt    REAL,
                sector        TEXT,
                parsed_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS filing_signals (
                id            TEXT PRIMARY KEY,
                filing_id     TEXT,
                company_code  TEXT,
                filing_date   TEXT,
                sector        TEXT,
                order_book    INTEGER DEFAULT 0,
                capex         INTEGER DEFAULT 0,
                credit_stress INTEGER DEFAULT 0,
                export        INTEGER DEFAULT 0,
                headcount     INTEGER DEFAULT 0,
                raw_text      TEXT,
                parsed_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS indicators (
                id                TEXT PRIMARY KEY,
                sector            TEXT NOT NULL,
                as_of_date        TEXT NOT NULL,
                revenue_momentum  REAL,
                margin_pressure   REAL,
                order_book_signal REAL,
                credit_stress     REAL,
                capex_intentions  REAL,
                export_outlook    REAL,
                composite_score   REAL,
                computed_at       TEXT DEFAULT (datetime('now'))
            );
        """)
        con.commit()
    finally:
        con.close()


def _upsert(con: sqlite3.Connection, table: str, df: pd.DataFrame, pk: str = "id"):
    df = df.drop_duplicates(subset=[pk], keep="last")
    cols = list(df.columns)
    ids = df[pk].tolist()
    if ids:
        placeholders = ",".join("?" * len(ids))
        con.execute(f"DELETE FROM {table} WHERE {pk} IN ({placeholders})", ids)
    rows = [
        tuple(None if (v is not None and pd.isna(v)) else v for v in row)
        for row in df.itertuples(index=False)
    ]
    col_str = ", ".join(cols)
    val_str = ", ".join("?" * len(cols))
    con.executemany(f"INSERT INTO {table} ({col_str}) VALUES ({val_str})", rows)


def _upsert_records(table: str, records: list[dict]):
    if not records:
        return
    con = get_connection()
    try:
        df = pd.DataFrame(records)
        _upsert(con, table, df)
        con.commit()
    finally:
        con.close()


def upsert_filings(records: list[dict]):
    _upsert_records("raw_filings", records)


def upsert_financials(records: list[dict]):
    _upsert_records("financials", records)


def upsert_signals(records: list[dict]):
    _upsert_records("filing_signals", records)


def upsert_indicators(records: list[dict]):
    _upsert_records("indicators", records)


def query(sql: str, params=None) -> pd.DataFrame:
    con = get_connection()
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return pd.DataFrame([dict(r) for r in rows], columns=cols)
    finally:
        con.close()
