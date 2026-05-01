import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
PDF_CACHE_DIR = BASE_DIR / "data" / "pdfs"

PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sme:sme@localhost:5432/sme_indicators")

# BSE API base
BSE_API_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_BASE = "https://www.bseindia.com"

# NSE API base
NSE_API_BASE = "https://www.nseindia.com/api"
NSE_BASE = "https://www.nseindia.com"

# Scraping behaviour
REQUEST_DELAY = .1       # seconds between requests
REQUEST_TIMEOUT = 5      # seconds
MAX_RETRIES = 3

# Default lookback window for scraping (days)
DEFAULT_DAYS_BACK = 90

# Max filings processed per parser run
BATCH_SIZE = 200

# BSE SME segment code
BSE_SME_SEGMENT = "BE"   # BSE SME Emerge segment marker

# Indicator weights for Composite SME Health Score
INDICATOR_WEIGHTS = {
    "revenue_momentum": 0.25,
    "margin_pressure": 0.20,
    "order_book_signal": 0.20,
    "credit_stress": 0.15,    # inverted — higher stress = lower score
    "capex_intentions": 0.10,
    "export_outlook": 0.10,
}

# Keywords for NLP signal extraction from filing text
KEYWORDS = {
    "order_book": ["order book", "order inflow", "order win", "new order", "order backlog", "pipeline"],
    "capex": ["capital expenditure", "capex", "plant expansion", "new facility", "greenfield", "brownfield"],
    "credit_stress": ["npa", "non-performing", "debt restructur", "moratorium", "default", "overdue", "insolvency"],
    "export": ["export", "forex", "foreign currency", "overseas", "international revenue", "global market"],
    "headcount": ["employee", "headcount", "workforce", "hiring", "manpower"],
}
