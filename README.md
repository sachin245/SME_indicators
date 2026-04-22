# SME Indicators Agent

A real-time intelligence platform that tracks leading indicators for Indian SME-listed companies on BSE (Emerge) and NSE SME segments. The system scrapes corporate filings, parses financial and textual data, computes sector-level health scores, and visualises them on an interactive dashboard.

---

## Table of Contents

1. [What This App Does](#what-this-app-does)
2. [Architecture Overview](#architecture-overview)
3. [Data Pipeline](#data-pipeline)
4. [Indicators Computed](#indicators-computed)
5. [Database Schema](#database-schema)
6. [Current Status](#current-status)
7. [Roadmap & Open Tasks](#roadmap--open-tasks)
8. [AWS Deployment Plan](#aws-deployment-plan)
9. [Local Setup](#local-setup)
10. [Environment Variables](#environment-variables)
11. [Running the Pipeline](#running-the-pipeline)

---

## What This App Does

Indian SME companies listed on BSE Emerge and NSE SME file quarterly results, annual reports, and ad-hoc announcements with the exchanges. These filings contain forward-looking signals — order book commentary, capex plans, export outlook, credit stress — that are buried in PDFs and XBRL XMLs and rarely aggregated at scale.

This platform:

- **Scrapes** BSE and NSE APIs daily for new corporate filings (announcements + financial results)
- **Parses** each filing: extracts structured financials from XBRL/XML files and business signals from PDFs via keyword scanning
- **Computes** six sector-level leading indicators plus a composite health score on a 0–100 scale
- **Visualises** everything on a Streamlit dashboard with heatmaps, trend lines, and a recent filings feed

The result is a daily pulse-check on SME sector health before the broader market catches up.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     agent.py (CLI)                       │
│            --scrape | --parse | --compute                │
└──────────┬──────────────┬──────────────┬────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────────────┐
    │ BSE Scraper │ │ NSE Scraper│ │  Indicator Engine   │
    │ (REST API)  │ │(Playwright)│ │  (indicators/)      │
    └──────┬──────┘ └─────┬──────┘ └────────────────────┘
           │              │
    ┌──────▼──────────────▼──────┐
    │        raw_filings          │
    │        (DuckDB)             │
    └──────┬──────────────┬──────┘
           │              │
    ┌──────▼──────┐ ┌─────▼──────┐
    │ PDF Parser  │ │XBRL Parser │
    │(PyMuPDF +   │ │ (lxml)     │
    │ pdfplumber) │ │            │
    └──────┬──────┘ └─────┬──────┘
           │              │
    ┌──────▼──────┐ ┌─────▼──────┐
    │filing_signals│ │ financials │
    └──────┬──────┘ └─────┬──────┘
           └──────┬────────┘
                  │
          ┌───────▼───────┐
          │  indicators   │
          │  (0-100 score)│
          └───────┬───────┘
                  │
          ┌───────▼───────┐
          │  Streamlit    │
          │  Dashboard    │
          └───────────────┘
```

### Component Breakdown

| Component | File | Responsibility |
|---|---|---|
| CLI Orchestrator | `agent.py` | Runs scrape → parse → compute pipeline end-to-end |
| Configuration | `config.py` | All constants: API URLs, indicator weights, NLP keywords |
| BSE Scraper | `scrapers/bse_scraper.py` | Fetches announcements and financial results from BSE REST API |
| NSE Scraper | `scrapers/nse_scraper.py` | Fetches from NSE API using Playwright for bot-detection bypass |
| PDF Parser | `parsers/pdf_parser.py` | Downloads PDFs, extracts text and tables, flags business signals |
| XBRL Parser | `parsers/xbrl_parser.py` | Parses XBRL/XML financial disclosures (revenue, EBITDA, PAT, debt) |
| Indicator Engine | `indicators/engine.py` | Aggregates signals and financials into 6 sector indicators + composite |
| Database Layer | `storage/database.py` | DuckDB schema, upsert operations, generic query interface |
| Dashboard | `dashboard/app.py` | Streamlit web UI: heatmaps, trend lines, filings feed |

---

## Data Pipeline

### Step 1 — Scrape

```bash
python agent.py --scrape --days 90
```

- **BSE Scraper** hits `https://api.bseindia.com/BseIndiaAPI/api` for:
  - `/AnnSubCategoryGetData/w` — corporate announcements
  - `/getFinancialResults/w` — quarterly/annual results
  - Falls back to HTML scraping if API is unavailable
- **NSE Scraper** uses Playwright to launch a headless Chrome browser, harvests session cookies from NSE's homepage (required to bypass bot detection), then hits `https://www.nseindia.com/api/corp-announcements` with pagination
- Each filing is deduplicated via an MD5 hash of `(exchange, company_code, filing_date, headline)` and upserted into `raw_filings`

### Step 2 — Parse

```bash
python agent.py --parse
```

Two parsers run in sequence on unprocessed filings:

- **PDF Parser**: Downloads PDFs to `data/pdfs/` cache → extracts full text (PyMuPDF) and tables (pdfplumber) → scans for NLP keyword categories (order_book, capex, credit_stress, export, headcount) → writes boolean signal flags to `filing_signals`
- **XBRL Parser**: Derives the XBRL/XML URL from the filing's PDF URL → fetches and parses XML with lxml → extracts revenue, EBITDA, PAT, total debt and period metadata → writes to `financials`

### Step 3 — Compute

```bash
python agent.py --compute
```

The indicator engine reads `financials` and `filing_signals`, groups by sector, computes six indicators (each normalised 0–100), and writes a composite weighted score to `indicators`.

---

## Indicators Computed

All indicators are normalised to a **0–100 scale**. Higher is always better (stress metrics are inverted).

| Indicator | Weight | Source | How It's Computed |
|---|---|---|---|
| Revenue Momentum | 25% | `financials` | Quarter-on-quarter revenue growth rate, normalised |
| Margin Pressure | 20% | `financials` | EBITDA / Revenue trend; higher = expanding margins |
| Order Book Signal | 20% | `filing_signals` | % of filings in past 90 days mentioning order book keywords |
| Credit Stress | 15% | `filing_signals` | % mentioning stress keywords, **inverted** so higher = less stress |
| Capex Intentions | 10% | `filing_signals` | % of filings mentioning capex / expansion keywords |
| Export Outlook | 10% | `filing_signals` | % mentioning export / forex / global keywords |
| **Composite Score** | 100% | All above | Weighted average of the six indicators |

**NLP Keyword Categories** (defined in `config.py`):

| Category | Sample Keywords |
|---|---|
| Order Book | "order book", "order inflow", "order pipeline", "order backlog" |
| Capex | "capital expenditure", "capex", "capacity expansion", "new plant" |
| Credit Stress | "npa", "default", "debt restructuring", "liquidity crunch", "stressed" |
| Export | "export", "foreign exchange", "forex", "overseas", "global markets" |
| Headcount | "hiring", "headcount", "workforce expansion", "recruitment" |

---

## Database Schema

Currently backed by **DuckDB** (embedded, file-based at `data/sme_indicators.duckdb`). No external database server is required for local development.

### `raw_filings`
Stores every filing scraped from BSE and NSE.

| Column | Type | Description |
|---|---|---|
| id | VARCHAR (PK) | MD5 deduplication hash |
| exchange | VARCHAR | "BSE" or "NSE" |
| company_code | VARCHAR | Exchange ticker/code |
| company_name | VARCHAR | Registered company name |
| filing_date | DATE | Date of filing |
| category | VARCHAR | "Announcement" or "Results" |
| headline | VARCHAR | Filing subject line |
| pdf_url | VARCHAR | Direct link to filing PDF |
| raw_json | TEXT | Full raw API response (JSON string) |
| scraped_at | TIMESTAMP | Ingestion timestamp |

### `financials`
Parsed quarterly/annual financial data from XBRL files.

| Column | Type | Description |
|---|---|---|
| filing_id | VARCHAR (FK) | Links to raw_filings.id |
| revenue | DOUBLE | Total revenue (INR, in filing units) |
| ebitda | DOUBLE | Operating profit |
| pat | DOUBLE | Profit after tax |
| total_debt | DOUBLE | Total borrowings |
| period_end | DATE | Financial period end date |
| period_type | VARCHAR | "Q" (quarterly) or "A" (annual) |
| parsed_at | TIMESTAMP | Parsing timestamp |

### `filing_signals`
Boolean NLP flags extracted from filing PDFs.

| Column | Type | Description |
|---|---|---|
| filing_id | VARCHAR (FK) | Links to raw_filings.id |
| order_book | BOOLEAN | Mentions order book / inflows |
| capex | BOOLEAN | Mentions capital expenditure |
| credit_stress | BOOLEAN | Mentions credit / liquidity stress |
| export | BOOLEAN | Mentions exports / forex |
| headcount | BOOLEAN | Mentions hiring / headcount |
| raw_text_excerpt | TEXT | First 5,000 chars of extracted text |
| parsed_at | TIMESTAMP | Parsing timestamp |

### `indicators`
Sector-level aggregated indicator scores.

| Column | Type | Description |
|---|---|---|
| sector | VARCHAR | Sector classification |
| revenue_momentum | DOUBLE | 0–100 score |
| margin_pressure | DOUBLE | 0–100 score |
| order_book_signal | DOUBLE | 0–100 score |
| credit_stress | DOUBLE | 0–100 score (inverted) |
| capex_intentions | DOUBLE | 0–100 score |
| export_outlook | DOUBLE | 0–100 score |
| composite_score | DOUBLE | Weighted composite 0–100 |
| as_of_date | DATE | Computation date |
| computed_at | TIMESTAMP | Computation timestamp |

---

## Current Status

### Completed

- [x] BSE scraper (REST API + HTML fallback)
- [x] NSE scraper (Playwright session, paginated)
- [x] PDF parser (PyMuPDF text + pdfplumber tables + keyword scanning)
- [x] XBRL parser (lxml-based, namespace-aware financial extraction)
- [x] Indicator engine (6 indicators, weighted composite, 0-100 normalisation)
- [x] DuckDB schema and upsert layer
- [x] Streamlit dashboard (heatmap, trend lines, filings table, refresh button)
- [x] CLI orchestrator (`agent.py` with `--scrape`, `--parse`, `--compute`, `--days`)
- [x] PDF caching to disk
- [x] Deduplication via MD5 hash

### In Progress / Known Gaps

- [ ] XBRL URL derivation is fragile (`.pdf → .xml` heuristic — fails for non-standard URLs)
- [ ] PDF batch limit is hardcoded at 200 filings per run (scalability bottleneck)
- [ ] No OCR for scanned/image PDFs (many older filings are image-only)
- [ ] Sector classification not yet implemented (filings are not tagged by sector)
- [ ] NSE Playwright session not cached across runs (re-launches browser every execution)
- [ ] No alerting or monitoring on pipeline failures
- [ ] No authentication on the Streamlit dashboard
- [ ] Financial extraction from PDF tables is heuristic-based, not production-grade

---

## Roadmap & Open Tasks

### Phase 1 — Data Quality (Next Up)

- [ ] **Sector tagging**: Map BSE/NSE company codes to NIC sector classifications using a reference table (BSE provides a downloadable master list)
- [ ] **OCR for scanned PDFs**: Integrate `pytesseract` or AWS Textract for image-based PDFs
- [ ] **Robust XBRL URL resolution**: Query BSE/NSE filing metadata APIs for the actual XBRL attachment URL instead of guessing from PDF URL
- [ ] **Playwright session caching**: Persist NSE cookies to disk with expiry handling to avoid relaunching Chrome on every run
- [ ] **Remove the 200-filing batch cap**: Process all pending filings per run, or implement a proper job queue

### Phase 2 — Infrastructure & Productionisation

- [ ] **Migrate from DuckDB to PostgreSQL (RDS)**: Required for multi-process writes and persistent cloud storage (see AWS Deployment Plan below)
- [ ] **Scheduler**: Replace manual CLI runs with a cron job or AWS EventBridge scheduled trigger
- [ ] **Containerise with Docker**: Package the pipeline and dashboard as separate Docker containers
- [ ] **CI/CD pipeline**: GitHub Actions for linting, testing, and automated Docker builds
- [ ] **Unit and integration tests**: Currently zero test coverage

### Phase 3 — Feature Expansion

- [ ] **Company-level drill-down**: Dashboard currently shows sector aggregates only; add per-company view
- [ ] **Historical backtesting**: Validate whether composite score leads actual earnings/price moves
- [ ] **Alerts**: Email / Slack notifications when a sector score crosses a threshold
- [ ] **LLM-powered summarisation**: Use an LLM to generate a one-paragraph narrative from each filing instead of just keyword flags
- [ ] **Peer comparison**: Show a company's indicators relative to its sector median
- [ ] **API layer**: Expose indicator data as a REST API (FastAPI) for downstream consumers

### Phase 4 — Scale

- [ ] **Real-time streaming**: Move from daily batch to event-driven (trigger parse immediately when a new filing is scraped)
- [ ] **Distributed scraping**: Run BSE and NSE scrapers in parallel workers (Celery / AWS SQS)
- [ ] **Vector search**: Embed filing text chunks into a vector DB for semantic similarity and trend detection
- [ ] **Dashboard authentication**: Add user login (Streamlit auth or reverse proxy with OAuth)

---

## AWS Deployment Plan

The target architecture deploys the pipeline as a scheduled batch job on AWS, with a managed database and a publicly accessible dashboard.

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                             │
│                                                              │
│  ┌──────────────┐    ┌─────────────────────────────────┐    │
│  │  EventBridge │───►│  ECS Fargate Task (pipeline)    │    │
│  │  (daily cron)│    │  agent.py --scrape --parse      │    │
│  └──────────────┘    │          --compute               │    │
│                       └────────────────┬────────────────┘    │
│                                        │                     │
│                              ┌─────────▼──────────┐         │
│                              │  Amazon RDS         │         │
│                              │  (PostgreSQL)       │         │
│                              │  - raw_filings      │         │
│                              │  - financials       │         │
│                              │  - filing_signals   │         │
│                              │  - indicators       │         │
│                              └─────────┬──────────┘         │
│                                        │                     │
│  ┌──────────────────────────────────────▼──────────────┐    │
│  │  ECS Fargate Service (dashboard)                     │    │
│  │  streamlit run dashboard/app.py                      │    │
│  │  ◄── ALB (HTTPS) ◄── Route 53 (custom domain)       │    │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  S3 Bucket   │    │  CloudWatch  │    │  Secrets Mgr  │  │
│  │  (PDF cache) │    │  (logs +     │    │  (DB creds,   │  │
│  │              │    │   alerts)    │    │   API keys)   │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### AWS Services Required

| Service | Purpose | Notes |
|---|---|---|
| **ECS Fargate** | Run pipeline and dashboard containers | Serverless; no EC2 to manage |
| **ECR** | Store Docker images | One repo for pipeline, one for dashboard |
| **Amazon RDS (PostgreSQL)** | Replace DuckDB for persistent, multi-process storage | `db.t3.micro` sufficient to start |
| **Amazon S3** | Persistent PDF cache (replace local `data/pdfs/`) | PDF files can be large; S3 scales cheaply |
| **EventBridge Scheduler** | Trigger daily pipeline run | Cron expression: `cron(0 2 * * ? *)` (2 AM IST) |
| **Application Load Balancer** | HTTPS termination for dashboard | With ACM certificate |
| **Route 53** | Custom domain for dashboard | Optional but recommended |
| **AWS Secrets Manager** | Store DB credentials, API keys | Never hardcode secrets |
| **CloudWatch Logs** | Centralised logging for pipeline and dashboard | Set up log groups per container |
| **CloudWatch Alarms** | Alert on pipeline failures or error spikes | SNS → email/Slack |

### Database Migration Steps (DuckDB → PostgreSQL on RDS)

1. **Provision RDS instance**
   - Engine: PostgreSQL 15
   - Instance class: `db.t3.micro` (upgrade later)
   - Multi-AZ: off initially, enable for production
   - Storage: 20 GB gp3 (auto-scaling enabled)
   - VPC: same as ECS tasks; no public access

2. **Update `storage/database.py`**
   - Replace `duckdb.connect()` with `psycopg2` / `sqlalchemy` connection
   - Connection string from environment variable: `DATABASE_URL`
   - Add connection pooling (`pgbouncer` or `sqlalchemy` pool)

3. **Run schema migration**
   - Port `init_db()` CREATE TABLE statements to PostgreSQL syntax
   - Add indexes on frequently queried columns:
     - `raw_filings(filing_date, exchange)`
     - `financials(filing_id, period_end)`
     - `indicators(sector, as_of_date)`

4. **Migrate PDF storage to S3**
   - Replace `data/pdfs/` local cache with `boto3` S3 reads/writes
   - Key pattern: `s3://sme-indicators-pdfs/{exchange}/{company_code}/{filename}`

5. **Store credentials in Secrets Manager**
   - Secret keys: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
   - Access via `boto3.client('secretsmanager')` at startup

### Deployment Steps (ECS Fargate)

1. Write `Dockerfile.pipeline` and `Dockerfile.dashboard`
2. Push images to ECR
3. Create ECS cluster (Fargate launch type)
4. Create two ECS task definitions: `sme-pipeline` and `sme-dashboard`
5. Create ECS service for the dashboard (desired count: 1, behind ALB)
6. Create EventBridge rule targeting the pipeline task definition
7. Configure CloudWatch log groups and alarms
8. Set all environment variables via ECS task definition secrets (pointing to Secrets Manager ARNs)

### Estimated Monthly AWS Cost (starting footprint)

| Service | Estimated Cost |
|---|---|
| RDS db.t3.micro (PostgreSQL) | ~$15/month |
| ECS Fargate — dashboard (0.25 vCPU, 0.5 GB, always-on) | ~$10/month |
| ECS Fargate — pipeline (1 vCPU, 2 GB, ~5 min/day) | ~$1/month |
| S3 (PDF storage, ~10 GB) | ~$0.25/month |
| ALB | ~$18/month |
| CloudWatch, ECR, misc | ~$5/month |
| **Total** | **~$50/month** |

---

## Local Setup

### Prerequisites

- Python 3.11+
- [Playwright](https://playwright.dev/python/) browsers installed
- Git

### Installation

```bash
git clone https://github.com/sachin245/SME_indicators.git
cd SME_indicators

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### Initialise the Database

```bash
python -c "from storage.database import init_db; init_db()"
```

This creates `data/sme_indicators.duckdb` with the four tables.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `DB_PATH` | Path to DuckDB file (local) | `data/sme_indicators.duckdb` |
| `PDF_CACHE_DIR` | Local PDF cache directory | `data/pdfs/` |
| `REQUEST_DELAY` | Seconds between HTTP requests | `1.5` |
| `LOOKBACK_DAYS` | Default days to scrape | `90` |
| `DATABASE_URL` | PostgreSQL URL (AWS deployment) | — |
| `AWS_REGION` | AWS region for S3/Secrets | `ap-south-1` |
| `S3_PDF_BUCKET` | S3 bucket for PDF cache (AWS) | — |

---

## Running the Pipeline

### Full pipeline (scrape + parse + compute)

```bash
python agent.py --scrape --parse --compute --days 90
```

### Individual stages

```bash
python agent.py --scrape --days 30      # Scrape last 30 days only
python agent.py --parse                 # Parse all unprocessed filings
python agent.py --compute               # Recompute indicators
```

### Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser.

---

## Project Structure

```
SME_indicators/
├── agent.py                  # CLI entrypoint and pipeline orchestrator
├── config.py                 # All configuration and constants
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .gitignore
├── scrapers/
│   ├── bse_scraper.py        # BSE filing scraper
│   └── nse_scraper.py        # NSE filing scraper (Playwright)
├── parsers/
│   ├── pdf_parser.py         # PDF text and signal extraction
│   └── xbrl_parser.py        # XBRL/XML financial data extraction
├── indicators/
│   └── engine.py             # Indicator computation and normalisation
├── storage/
│   └── database.py           # DuckDB schema and data access layer
└── dashboard/
    └── app.py                # Streamlit dashboard
```

---

## Contributing

1. Fork the repo and create a feature branch
2. Make changes with tests where applicable
3. Open a pull request against `main`

---

*Built to surface forward-looking signals from Indian SME filings before the market does.*
