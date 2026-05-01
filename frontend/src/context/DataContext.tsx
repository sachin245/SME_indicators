import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { IndicatorRow, Summary, Company, Filing, Financial, SignalTrend } from '../types'

export interface AppData {
  indicatorsLatest: IndicatorRow[]
  indicatorHistory: IndicatorRow[]
  summary: Summary | null
  companies: Company[]
  filings: Filing[]
  financials: Financial[]
  signalTrend: SignalTrend[]
  sectors: string[]
  categories: string[]
  loading: boolean
  error: string | null
  generatedAt: string | null
}

const empty: AppData = {
  indicatorsLatest: [],
  indicatorHistory: [],
  summary: null,
  companies: [],
  filings: [],
  financials: [],
  signalTrend: [],
  sectors: [],
  categories: [],
  loading: true,
  error: null,
  generatedAt: null,
}

const DataContext = createContext<AppData>(empty)

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<AppData>(empty)

  useEffect(() => {
    fetch('/data/data.json')
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load data.json: ${res.status}`)
        return res.json()
      })
      .then((json) => {
        const filings: Filing[] = json.filings ?? []
        const companies: Company[] = json.companies ?? []
        setData({
          indicatorsLatest: json.indicators_latest ?? [],
          indicatorHistory: json.indicator_history ?? [],
          summary: json.summary ?? null,
          companies,
          filings,
          financials: json.financials ?? [],
          signalTrend: json.signal_trend ?? [],
          sectors: ([...new Set(companies.map((c) => c.sector).filter(Boolean))] as string[]).sort(),
          categories: ([...new Set(filings.map((f) => f.category).filter(Boolean))] as string[]).sort(),
          loading: false,
          error: null,
          generatedAt: json.generated_at ?? null,
        })
      })
      .catch((err) => {
        setData((prev) => ({ ...prev, loading: false, error: String(err) }))
      })
  }, [])

  return <DataContext.Provider value={data}>{children}</DataContext.Provider>
}

export const useData = () => useContext(DataContext)
