"""
SME Indicators Agent — main orchestrator.

Usage:
    python agent.py --scrape --parse --compute        # full pipeline
    python agent.py --scrape                          # scrape only
    python agent.py --parse                           # parse only
    python agent.py --compute                         # recompute indicators
    python agent.py --scrape --days 30                # scrape last 30 days
"""

import argparse
import sys
import time
from datetime import datetime


def _header(step: str):
    print(f"\n{'='*60}")
    print(f"  {step}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


def run_scrape(days: int):
    _header("STEP 1 — Scraping BSE & NSE filings")
    from scrapers import bse_scraper, nse_scraper
    from storage.database import init_db
    init_db()

    bse_records = bse_scraper.run(days_back=days)
    time.sleep(2)
    try:
        nse_records = nse_scraper.run(days_back=days)
    except Exception as e:
        print(f"[Scrape] NSE scraper failed (BSE data still saved): {e}")
        nse_records = []

    total = len(bse_records) + len(nse_records)
    print(f"\n[Scrape] Done. {total} total filings saved.")
    return total


def run_parse():
    _header("STEP 2 — Parsing PDFs & XBRL")
    from parsers import pdf_parser, xbrl_parser
    pdf_parser.run()
    xbrl_parser.run()
    print("\n[Parse] Done.")


def run_compute():
    _header("STEP 3 — Computing indicators")
    from indicators.engine import run as engine_run
    engine_run()
    print("\n[Compute] Done.")


def main():
    parser = argparse.ArgumentParser(
        description="SME Indicators Agent — scrapes BSE/NSE filings and computes SME leading indicators"
    )
    parser.add_argument("--scrape",  action="store_true", help="Scrape BSE & NSE filings")
    parser.add_argument("--parse",   action="store_true", help="Parse downloaded filings (PDF + XBRL)")
    parser.add_argument("--compute", action="store_true", help="Compute indicators from parsed data")
    parser.add_argument("--days",    type=int, default=90, help="Days to look back when scraping (default: 90)")
    args = parser.parse_args()

    if not any([args.scrape, args.parse, args.compute]):
        parser.print_help()
        sys.exit(0)

    start = time.time()
    print(f"\nSME Indicators Agent")
    print(f"Lookback: {args.days} days")

    if args.scrape:
        run_scrape(args.days)

    if args.parse:
        run_parse()

    if args.compute:
        run_compute()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
