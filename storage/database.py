import os
import pandas as pd
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sme:sme@localhost:5432/sme_indicators")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute("""
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
                    raw_json      TEXT,
                    scraped_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financials (
                    id            VARCHAR PRIMARY KEY,
                    filing_id     VARCHAR,
                    company_code  VARCHAR NOT NULL,
                    company_name  VARCHAR,
                    exchange      VARCHAR,
                    period_end    DATE,
                    period_type   VARCHAR,
                    revenue       DOUBLE PRECISION,
                    ebitda        DOUBLE PRECISION,
                    pat           DOUBLE PRECISION,
                    total_debt    DOUBLE PRECISION,
                    sector        VARCHAR,
                    parsed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
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
                    raw_text      TEXT,
                    parsed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    id                    VARCHAR PRIMARY KEY,
                    sector                VARCHAR NOT NULL,
                    as_of_date            DATE NOT NULL,
                    revenue_momentum      DOUBLE PRECISION,
                    margin_pressure       DOUBLE PRECISION,
                    order_book_signal     DOUBLE PRECISION,
                    credit_stress         DOUBLE PRECISION,
                    capex_intentions      DOUBLE PRECISION,
                    export_outlook        DOUBLE PRECISION,
                    composite_score       DOUBLE PRECISION,
                    computed_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        con.commit()
    finally:
        con.close()


def _upsert(cur, table: str, df: pd.DataFrame, pk: str = "id"):
    df = df.drop_duplicates(subset=[pk], keep="last")
    cols = list(df.columns)
    ids = df[pk].tolist()
    if ids:
        cur.execute(f"DELETE FROM {table} WHERE {pk} = ANY(%s)", (ids,))
    rows = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False)]
    psycopg2.extras.execute_values(
        cur,
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s",
        rows,
    )


def _upsert_records(table: str, records: list[dict]):
    if not records:
        return
    con = get_connection()
    try:
        df = pd.DataFrame(records)
        with con.cursor() as cur:
            _upsert(cur, table, df)
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
        with con.cursor() as cur:
            cur.execute(sql, params or [])
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return pd.DataFrame(rows, columns=cols)
    finally:
        con.close()
