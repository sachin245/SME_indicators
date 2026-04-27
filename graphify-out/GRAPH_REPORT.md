# Graph Report - .  (2026-04-27)

## Corpus Check
- Corpus is ~14,393 words - fits in a single context window. You may not need a graph.

## Summary
- 274 nodes · 397 edges · 23 communities detected
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Indicators & AWS Deployment|Indicators & AWS Deployment]]
- [[_COMMUNITY_Frontend API Layer|Frontend API Layer]]
- [[_COMMUNITY_FastAPI Backend Routers|FastAPI Backend Routers]]
- [[_COMMUNITY_Indicator Engine|Indicator Engine]]
- [[_COMMUNITY_PDF Parser|PDF Parser]]
- [[_COMMUNITY_XBRL Parser|XBRL Parser]]
- [[_COMMUNITY_Scraper Docs & Frontend Entry|Scraper Docs & Frontend Entry]]
- [[_COMMUNITY_Pipeline & Database Storage|Pipeline & Database Storage]]
- [[_COMMUNITY_BSE Scraper|BSE Scraper]]
- [[_COMMUNITY_NSE Scraper|NSE Scraper]]
- [[_COMMUNITY_Pipeline Orchestrator|Pipeline Orchestrator]]
- [[_COMMUNITY_Streamlit Dashboard|Streamlit Dashboard]]
- [[_COMMUNITY_Frontend Color Utils|Frontend Color Utils]]
- [[_COMMUNITY_Signal Badge Component|Signal Badge Component]]
- [[_COMMUNITY_Filings Browser Page|Filings Browser Page]]
- [[_COMMUNITY_Company Browser Page|Company Browser Page]]
- [[_COMMUNITY_FastAPI App Entry|FastAPI App Entry]]
- [[_COMMUNITY_React App Router|React App Router]]
- [[_COMMUNITY_Score Gauge Component|Score Gauge Component]]
- [[_COMMUNITY_URL Filters Hook|URL Filters Hook]]
- [[_COMMUNITY_Overview Dashboard Page|Overview Dashboard Page]]
- [[_COMMUNITY_Module  Config|Module / Config]]
- [[_COMMUNITY_Module  Config|Module / Config]]

## God Nodes (most connected - your core abstractions)
1. `query()` - 14 edges
2. `execute_query()` - 12 edges
3. `apiFetch()` - 12 edges
4. `run()` - 12 edges
5. `Indicator Engine` - 11 edges
6. `_normalize()` - 9 edges
7. `parse_filing()` - 9 edges
8. `run()` - 9 edges
9. `get_connection()` - 8 edges
10. `run()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Streamlit Dashboard` --semantically_similar_to--> `Frontend index.html (React/TSX)`  [INFERRED] [semantically similar]
  README.md → frontend/index.html
- `Frontend index.html (React/TSX)` --semantically_similar_to--> `fastapi 0.115.6`  [INFERRED] [semantically similar]
  frontend/index.html → requirements.txt
- `run_scrape()` --calls--> `init_db()`  [INFERRED]
  C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\agent.py → C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\storage\database.py
- `run_scrape()` --calls--> `run()`  [INFERRED]
  C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\agent.py → C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\scrapers\nse_scraper.py
- `run_parse()` --calls--> `run()`  [INFERRED]
  C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\agent.py → C:\Users\sachi\OneDrive\Documents\GitHub\SME_indicators\scrapers\nse_scraper.py

## Hyperedges (group relationships)
- **SME Indicators Data Pipeline: Scrape to Parse to Compute** — readme_agent_py, readme_bse_scraper, readme_nse_scraper, readme_pdf_parser, readme_xbrl_parser, readme_indicator_engine, readme_database_layer [EXTRACTED 1.00]
- **Six Indicators Aggregated into Composite Score** — readme_revenue_momentum, readme_margin_pressure, readme_order_book_signal, readme_credit_stress, readme_capex_intentions, readme_export_outlook, readme_composite_score [EXTRACTED 1.00]
- **AWS Production Deployment Stack** — readme_ecs_fargate, readme_amazon_rds, readme_amazon_s3, readme_eventbridge, readme_cloudwatch, readme_secrets_manager [EXTRACTED 1.00]

## Communities

### Community 0 - "Indicators & AWS Deployment"
Cohesion: 0.09
Nodes (31): Amazon RDS (PostgreSQL), Amazon S3 PDF Cache, AWS Deployment Plan, Capex Intentions Indicator, CloudWatch Logs and Alarms, Composite Health Score (0-100), config.py Configuration, Credit Stress Indicator (+23 more)

### Community 1 - "Frontend API Layer"
Cohesion: 0.13
Nodes (11): apiFetch(), fetchCategories(), fetchCompanies(), fetchFilings(), fetchSignalTrend(), fetchFinancials(), handleFetch(), fetchIndicatorHistory() (+3 more)

### Community 2 - "FastAPI Backend Routers"
Cohesion: 0.16
Nodes (12): execute_count(), execute_query(), _build_filings_where(), get_filings(), get_signal_trend(), list_categories(), list_companies(), get_financials() (+4 more)

### Community 3 - "Indicator Engine"
Cohesion: 0.22
Nodes (20): query(), compute_capex_intentions(), compute_composite(), compute_credit_stress(), compute_export_outlook(), compute_margin_pressure(), compute_order_book_signal(), compute_revenue_momentum() (+12 more)

### Community 4 - "PDF Parser"
Cohesion: 0.22
Nodes (16): download_pdf(), extract_tables(), extract_text(), _find_financial_in_tables(), parse_filing(), _parse_number(), _pdf_local_path(), PDF parser — downloads filing PDFs and extracts:   - Financial figures (revenue (+8 more)

### Community 5 - "XBRL Parser"
Cohesion: 0.25
Nodes (14): _fetch_xbrl(), _filing_fin_id(), _local_name(), parse_filing(), _parse_value(), parse_xbrl_bytes(), XBRL parser — parses MCA-mandated XBRL financial data from BSE/NSE filings. Use, Download and parse XBRL for a single filing. (+6 more)

### Community 6 - "Scraper Docs & Frontend Entry"
Cohesion: 0.13
Nodes (16): Frontend index.html (React/TSX), frontend/src/main.tsx Entry Point, agent.py CLI Orchestrator, BSE REST API, BSE Scraper, MD5 Deduplication Strategy, NSE API, NSE Scraper (+8 more)

### Community 7 - "Pipeline & Database Storage"
Cohesion: 0.31
Nodes (9): get_connection(), init_db(), upsert_filings(), upsert_financials(), upsert_indicators(), upsert_signals(), get_status(), _run() (+1 more)

### Community 8 - "BSE Scraper"
Cohesion: 0.33
Nodes (11): _filing_id(), _get(), BSE scraper — targets BSE SME Emerge segment and mainboard SME-sized companies., HTML fallback for BSE announcements page., Fetch financial result filings from BSE., Main entry point — scrape and persist BSE filings., Fetch corporate announcements for BSE SME Emerge companies., run() (+3 more)

### Community 9 - "NSE Scraper"
Cohesion: 0.35
Nodes (11): _filing_id(), _get(), _get_session_cookies(), NSE scraper — targets NSE Emerge (SME platform) and SME-sized NSE-listed compani, Fetch financial result filings from NSE., Main entry point — scrape and persist NSE filings., Use Playwright to load NSE homepage and extract session cookies., Fetch corporate announcements from NSE. (+3 more)

### Community 10 - "Pipeline Orchestrator"
Cohesion: 0.64
Nodes (6): _header(), main(), SME Indicators Agent — main orchestrator.  Usage:     python agent.py --scrap, run_compute(), run_parse(), run_scrape()

### Community 11 - "Streamlit Dashboard"
Cohesion: 0.48
Nodes (5): _flag(), load_indicator_history(), load_indicators(), load_recent_filings(), Streamlit dashboard for SME Indicators. Run with: streamlit run dashboard/app.p

### Community 12 - "Frontend Color Utils"
Cohesion: 0.6
Nodes (3): fmtCrore(), scoreTextClass(), scoreToHsl()

### Community 13 - "Signal Badge Component"
Cohesion: 0.67
Nodes (2): SignalBadge(), SignalBadgeRow()

### Community 14 - "Filings Browser Page"
Cohesion: 0.67
Nodes (2): resetFilters(), toggleSignal()

### Community 15 - "Company Browser Page"
Cohesion: 0.67
Nodes (2): handleSearch(), handleSector()

### Community 16 - "FastAPI App Entry"
Cohesion: 0.67
Nodes (1): health()

### Community 17 - "React App Router"
Cohesion: 0.67
Nodes (1): App()

### Community 18 - "Score Gauge Component"
Cohesion: 0.67
Nodes (1): arcPoint()

### Community 19 - "URL Filters Hook"
Cohesion: 0.67
Nodes (1): useFilters()

### Community 20 - "Overview Dashboard Page"
Cohesion: 0.67
Nodes (1): KpiCard()

### Community 59 - "Module / Config"
Cohesion: 1.0
Nodes (1): pandas 2.2.3

### Community 60 - "Module / Config"
Cohesion: 1.0
Nodes (1): python-dotenv 1.0.1

## Knowledge Gaps
- **50 isolated node(s):** `Min-max normalize to 0–100. Invert for stress indicators.`, `QoQ revenue growth rate per sector, normalized 0–100.`, `EBITDA margin trend — higher margin = higher score.`, `% of recent filings per sector with order book mentions.`, `% of filings with credit stress mentions — inverted so higher = better.` (+45 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Signal Badge Component`** (4 nodes): `SignalBadge.tsx`, `SignalBadge.tsx`, `SignalBadge()`, `SignalBadgeRow()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Filings Browser Page`** (4 nodes): `FilingsBrowser.tsx`, `resetFilters()`, `toggleSignal()`, `FilingsBrowser.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Company Browser Page`** (4 nodes): `CompanyBrowser.tsx`, `handleSearch()`, `handleSector()`, `CompanyBrowser.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `FastAPI App Entry`** (3 nodes): `main.py`, `main.py`, `health()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `React App Router`** (3 nodes): `App()`, `App.tsx`, `App.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Score Gauge Component`** (3 nodes): `ScoreGauge.tsx`, `ScoreGauge.tsx`, `arcPoint()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `URL Filters Hook`** (3 nodes): `useFilters.ts`, `useFilters.ts`, `useFilters()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Overview Dashboard Page`** (3 nodes): `Overview.tsx`, `Overview.tsx`, `KpiCard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module / Config`** (1 nodes): `pandas 2.2.3`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module / Config`** (1 nodes): `python-dotenv 1.0.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `query()` connect `Indicator Engine` to `Streamlit Dashboard`, `PDF Parser`, `XBRL Parser`, `Pipeline & Database Storage`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `upsert_filings()` connect `Pipeline & Database Storage` to `BSE Scraper`, `NSE Scraper`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `run()` connect `PDF Parser` to `Indicator Engine`, `Pipeline & Database Storage`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `query()` (e.g. with `load_indicators()` and `load_recent_filings()`) actually correct?**
  _`query()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `execute_query()` (e.g. with `get_filings()` and `list_categories()`) actually correct?**
  _`execute_query()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `apiFetch()` (e.g. with `fetchFilings()` and `fetchCompanies()`) actually correct?**
  _`apiFetch()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Min-max normalize to 0–100. Invert for stress indicators.`, `QoQ revenue growth rate per sector, normalized 0–100.`, `EBITDA margin trend — higher margin = higher score.` to the rest of the system?**
  _50 weakly-connected nodes found - possible documentation gaps or missing edges._