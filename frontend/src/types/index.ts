export interface IndicatorRow {
  id: string
  sector: string
  as_of_date: string
  revenue_momentum: number | null
  margin_pressure: number | null
  order_book_signal: number | null
  credit_stress: number | null
  capex_intentions: number | null
  export_outlook: number | null
  composite_score: number | null
  computed_at: string | null
}

export interface Filing {
  id: string
  exchange: string
  company_code: string
  company_name: string | null
  filing_date: string
  category: string | null
  subcategory: string | null
  headline: string | null
  pdf_url: string | null
  order_book: boolean
  capex: boolean
  credit_stress: boolean
  export: boolean
  headcount: boolean
  sector: string
}

export interface Financial {
  company_code: string
  company_name: string | null
  exchange: string
  sector: string
  period_end: string
  period_type: string
  revenue: number | null
  ebitda: number | null
  pat: number | null
  total_debt: number | null
}

export interface Company {
  company_code: string
  company_name: string | null
  exchange: string
  sector: string
  filing_count: number
}

export interface Summary {
  total_filings: number
  total_companies: number
  composite_score: number
  signal_counts: {
    order_book: number
    capex: number
    credit_stress: number
    export: number
    headcount: number
  }
}

export interface SignalTrend {
  bucket: string
  total: number
  order_book_rate: number
  capex_rate: number
  credit_stress_rate: number
  export_rate: number
  headcount_rate: number
}

export interface PagedResponse<T> {
  data: T[]
  total: number
  page: number
  page_size: number
}

export interface Filters {
  from: string
  to: string
  exchange: string[]
}
