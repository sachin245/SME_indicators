import duckdb
import pandas as pd
from config import DB_PATH


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def init_db():
    con = get_connection()
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw_filings (
                id            VARCHAR PRIMARY KEY,
                exchange      VARCHAR NOT NULL,
                company_code  VARCHAR NOT NULL,
                company_name  VARCHAR,
                filing_date   DATE,
                category      VARCHAR,
                subcategory   VARCHAR,
                headline      VARCHAR,
                pdf_url       VARCHAR,
                pdf_local     VARCHAR,
                raw_json      VARCHAR,
                scraped_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS financials (
                id            VARCHAR PRIMARY KEY,
                filing_id     VARCHAR,
                company_code  VARCHAR NOT NULL,
                company_name  VARCHAR,
                exchange      VARCHAR,
                period_end    DATE,
                period_type   VARCHAR,
                revenue       DOUBLE,
                ebitda        DOUBLE,
                pat           DOUBLE,
                total_debt    DOUBLE,
                sector        VARCHAR,
                parsed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS filing_signals (
                id            VARCHAR PRIMARY KEY,
                filing_id     VARCHAR,
                company_code  VARCHAR,
                filing_date   DATE,
                sector        VARCHAR,
                order_book    BOOLEAN DEFAULT FALSE,
                capex         BOOLEAN DEFAULT FALSE,
                credit_stress BOOLEAN DEFAULT FALSE,
                export        BOOLEAN DEFAULT FALSE,
                headcount     BOOLEAN DEFAULT FALSE,
                raw_text      VARCHAR,
                parsed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id                    VARCHAR PRIMARY KEY,
                sector                VARCHAR NOT NULL,
                as_of_date            DATE NOT NULL,
                revenue_momentum      DOUBLE,
                margin_pressure       DOUBLE,
                order_book_signal     DOUBLE,
                credit_stress         DOUBLE,
                capex_intentions      DOUBLE,
                export_outlook        DOUBLE,
                composite_score       DOUBLE,
                computed_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    finally:
        con.close()


def _upsert(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame, pk: str = "id"):
    df = df.drop_duplicates(subset=[pk], keep="last")
    cols = ", ".join(df.columns)
    ids = df[pk].tolist()
    if ids:
        placeholders = ", ".join(["?" for _ in ids])
        con.execute(f"DELETE FROM {table} WHERE {pk} IN ({placeholders})", ids)
    con.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM df")


def _upsert_records(table: str, records: list[dict]):
    if not records:
        return
    con = get_connection()
    try:
        df = pd.DataFrame(records)
        _upsert(con, table, df)
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
        return con.execute(sql, params or []).df()
    finally:
        con.close()
