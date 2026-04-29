import { apiFetch } from './client'

export interface DataHealth {
  total_filings: number
  pdf_parsed: number
  xbrl_parsed: number
  indicator_rows: number
  latest_filing: string | null
  earliest_filing: string | null
  last_scrape: string | null
  last_compute: string | null
  classified_sectors: number
  unclassified_signals: number
  pdf_parse_coverage_pct: number
  status: 'ok' | 'degraded'
}

export const fetchDataHealth = () => apiFetch<DataHealth>('/api/health/data')
