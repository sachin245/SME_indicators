"""
Sector classifier for Indian listed companies.

Strategy: keyword-based classification on company name. This is a pragmatic
fallback until a proper BSE/NSE master CSV mapping is wired in. Order matters
in SECTOR_RULES — the first matching rule wins, so put more specific terms
first (e.g. "pharma" before "chem").

Public API:
    classify(name: str) -> str            # single-name classifier
    backfill_sectors() -> dict            # backfill all *_signals + financials
"""

from __future__ import annotations

import re
from typing import Iterable

import duckdb

from config import DB_PATH


# Order matters: first match wins. Each rule = (sector_label, [keyword,...]).
SECTOR_RULES: list[tuple[str, list[str]]] = [
    ("IT & Software",          ["technolog", "infotech", "software", "infosys", "tcs",
                                "wipro", "hcl tech", "mindtree", "mphasis", "persistent",
                                "ltimind", "coforge", "datamatics", "cyient", "zensar"]),
    ("Pharma & Healthcare",    ["pharma", "drug", "biotech", "lifescience", "life science",
                                "healthcare", "hospital", "medi", "diagnost", "cipla",
                                "lupin", "dr reddy", "sun pharma", "aurobindo", "torrent pharma",
                                "glenmark", "biocon", "ipca", "wockhardt"]),
    ("Banks & Financial Svcs", ["bank", "finance", "capital", "fincorp", "fintech", "nbfc",
                                "lending", "credit", "loan", "housing finance", "hdfc",
                                "icici", "kotak", "axis", "sbi ", "yes bank", "bajaj fin",
                                "muthoot", "manappuram", "shriram", "cholamandalam"]),
    ("Insurance",              ["insurance", "assurance", "lic ", "life ins", "general ins"]),
    ("Auto & Components",      ["auto", "motor", "vehicle", "tyre", "tire", "bearing",
                                "axles", "forging", "tata motor", "maruti", "mahindra",
                                "bajaj auto", "eicher", "hero ", "tvs", "ashok leyland",
                                "bosch", "mrf", "ceat", "exide", "amara raja"]),
    ("Capital Goods",          ["engineering", "engg", "industries", "industrial",
                                "machine", "equipment", "tools", "fabrica", "valve",
                                "pump", "compressor", "abb", "siemens", "thermax",
                                "cummins", "bhel", "l&t", "larsen", "kirloskar"]),
    ("Metals & Mining",        ["steel", "iron", "metal", "mining", "ore", "aluminium",
                                "aluminum", "copper", "zinc", "tata steel", "jsw",
                                "jindal", "sail", "hindalco", "vedanta", "nmdc", "coal "]),
    ("Energy & Power",         ["power", "energy", "electric", "ntpc", "petroleum",
                                "oil ", "gas", "petro", "refiner", "ongc", "ioc",
                                "bpcl", "hpcl", "reliance industries", "adani power",
                                "tata power", "torrent power"]),
    ("Chemicals",              ["chemical", "fertili", "agrochem", "specialty chem",
                                "polymer", "pidilite", "asian paint", "berger", "kansai",
                                "sudarshan", "deepak nitri", "aarti"]),
    ("Cement & Construction",  ["cement", "construction", "infrastructure", "infra ",
                                "ultratech", "ambuja", "shree cement", "acc ", "dalmia",
                                "ramco cement"]),
    ("Real Estate",            ["realty", "real estate", "developers", "estate",
                                "godrej propert", "dlf ", "oberoi realty", "prestige",
                                "brigade", "sobha", "phoenix mill"]),
    ("Textiles & Apparel",     ["textile", "apparel", "garment", "fabric", "spinning",
                                "yarn", "denim", "raymond", "arvind", "vardhman"]),
    ("FMCG & Consumer",        ["consumer", "fmcg", "foods", "beverag", "dairy",
                                "personal care", "hindustan unilever", "itc ",
                                "nestle", "britannia", "marico", "dabur", "godrej consumer",
                                "colgate", "emami", "tata consumer"]),
    ("Retail",                 ["retail", "departmental", "trent ", "avenue super",
                                "dmart", "shoppers stop", "vmart", "aditya birla fashion"]),
    ("Media & Entertainment",  ["media", "entertain", "broadcast", "television", "tv ",
                                "film", "cinema", "music", "pvr", "inox leisure",
                                "sun tv", "zee ", "network18", "saregama"]),
    ("Telecom",                ["telecom", "communication", "wireless", "cellular",
                                "bharti airtel", "idea cellular", "vodafone", "tata comm"]),
    ("Logistics & Transport",  ["logistic", "transport", "shipping", "courier",
                                "freight", "container", "warehousing", "aegis",
                                "blue dart", "concor", "gati", "vrl", "tci ", "delhivery"]),
    ("Aviation",               ["airline", "aviation", "airways", "indigo", "spicejet",
                                "interglobe avia"]),
    ("Hotels & Tourism",       ["hotel", "resort", "tourism", "leisure", "travel",
                                "indian hotels", "eih ", "lemon tree", "mahindra holiday"]),
    ("Agro & Food Processing", ["agro", "agri ", "agritech", "seeds", "sugar", "tea ",
                                "coffee", "rice", "edible oil", "balrampur", "shree renuka"]),
    ("Diversified",            ["enterprises", "diversified", "holdings", "group ",
                                "international", "global"]),
]

_FALLBACK = "Diversified"
_UNKNOWN = "Unknown"


def classify(company_name: str | None) -> str:
    """Return the best-matching sector for a company name. Returns 'Unknown'
    if name is missing/empty; otherwise always returns a non-empty label
    (falling back to 'Diversified' for unmatched names)."""
    if not company_name:
        return _UNKNOWN
    n = company_name.lower()
    for sector, keywords in SECTOR_RULES:
        for kw in keywords:
            if kw in n:
                return sector
    # Last-ditch heuristic: very short / obviously generic names → Diversified
    return _FALLBACK


def classify_many(names: Iterable[str | None]) -> list[str]:
    return [classify(n) for n in names]


# ── Backfill helpers ────────────────────────────────────────────────────────

def _connect():
    return duckdb.connect(str(DB_PATH))


def backfill_sectors() -> dict:
    """Walk raw_filings, classify every distinct company, and propagate the
    sector into filing_signals.sector and financials.sector wherever it is
    NULL or 'Unknown'. Idempotent — safe to re-run."""
    con = _connect()
    try:
        rows = con.execute(
            "SELECT DISTINCT company_code, ANY_VALUE(company_name) AS company_name "
            "FROM raw_filings WHERE company_code IS NOT NULL GROUP BY company_code"
        ).fetchall()

        # Build mapping table in-DB so we can JOIN-update efficiently
        mapping = [(code, classify(name)) for code, name in rows]
        con.execute(
            "CREATE OR REPLACE TEMP TABLE _sector_map (company_code VARCHAR, sector VARCHAR)"
        )
        con.executemany(
            "INSERT INTO _sector_map VALUES (?, ?)", mapping
        )

        # Update filing_signals
        sig_updated = con.execute("""
            UPDATE filing_signals fs
            SET sector = m.sector
            FROM _sector_map m
            WHERE fs.company_code = m.company_code
              AND (fs.sector IS NULL OR fs.sector = '' OR fs.sector = 'Unknown')
              AND m.sector <> 'Unknown'
        """).fetchone()

        # Update financials
        fin_updated = con.execute("""
            UPDATE financials f
            SET sector = m.sector
            FROM _sector_map m
            WHERE f.company_code = m.company_code
              AND (f.sector IS NULL OR f.sector = '' OR f.sector = 'Unknown')
              AND m.sector <> 'Unknown'
        """).fetchone()

        # Distribution after backfill
        dist = con.execute("""
            SELECT sector, COUNT(*) AS n
            FROM filing_signals
            GROUP BY sector ORDER BY n DESC
        """).fetchall()

        return {
            "companies_classified": len(mapping),
            "filing_signals_updated": sig_updated[0] if sig_updated else 0,
            "financials_updated": fin_updated[0] if fin_updated else 0,
            "sector_distribution": dict(dist),
        }
    finally:
        con.close()


if __name__ == "__main__":
    import json
    print(json.dumps(backfill_sectors(), indent=2, default=str))
