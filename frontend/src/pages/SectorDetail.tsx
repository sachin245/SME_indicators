import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import GlobalFilterBar from '../components/GlobalFilterBar'
import FinancialsBarChart from '../components/FinancialsBarChart'
import ScoreGauge from '../components/ScoreGauge'
import { useFilters } from '../hooks/useFilters'
import { fetchIndicatorHistory, fetchLatestIndicators } from '../api/indicators'
import { fetchCompanies, fetchSignalTrend } from '../api/filings'
import { fetchFinancials } from '../api/financials'
import { INDICATOR_LABELS, SIGNAL_COLORS } from '../utils/colors'

const INDICATOR_KEYS = [
  'revenue_momentum', 'margin_pressure', 'order_book_signal',
  'credit_stress', 'capex_intentions', 'export_outlook',
] as const

export default function SectorDetail() {
  const { sector } = useParams<{ sector: string }>()
  const navigate = useNavigate()
  const { from, to, exchange } = useFilters()
  const decoded = decodeURIComponent(sector ?? '')

  const { data: history = [] } = useQuery({
    queryKey: ['indicators', 'history', decoded, from, to],
    queryFn: () => fetchIndicatorHistory({ sector: decoded, from_date: from, to_date: to }),
  })

  const { data: latest = [] } = useQuery({
    queryKey: ['indicators', 'latest'],
    queryFn: fetchLatestIndicators,
  })

  const latestRow = latest.find((r) => r.sector === decoded)

  const { data: companiesRes } = useQuery({
    queryKey: ['companies', decoded, exchange],
    queryFn: () => fetchCompanies({ sector: decoded, exchange: exchange.length ? exchange : undefined, page_size: 100 }),
  })

  const { data: financials = [] } = useQuery({
    queryKey: ['financials', 'sector', decoded, from, to],
    queryFn: () => fetchFinancials({
      sector: decoded, from_date: from, to_date: to, limit: 500,
    }),
  })

  const { data: signalTrend = [] } = useQuery({
    queryKey: ['signals', 'trend', decoded, from, to],
    queryFn: () => fetchSignalTrend({ sector: decoded, from_date: from, to_date: to }),
  })

  // Pivot indicator history into [{date, revenue_momentum: N, ...}]
  const indicatorTrendData = history.map((r) => ({
    date: r.as_of_date,
    ...INDICATOR_KEYS.reduce((acc, k) => ({ ...acc, [k]: r[k] }), {}),
  }))

  const signalKeys = ['order_book_rate', 'capex_rate', 'credit_stress_rate', 'export_rate', 'headcount_rate']
  const signalLabels: Record<string, string> = {
    order_book_rate: 'Order Book', capex_rate: 'Capex',
    credit_stress_rate: 'Credit Stress', export_rate: 'Export', headcount_rate: 'Headcount',
  }

  const companies = companiesRes?.data ?? []

  return (
    <div>
      <GlobalFilterBar />
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(-1)} className="btn-ghost">
          <ArrowLeft size={15} /> Back
        </button>
        <h1 className="text-xl font-bold text-slate-100">{decoded}</h1>
        {latestRow && (
          <span className="text-slate-400 text-sm ml-2">
            Latest composite: <span className="font-semibold text-slate-200">{Math.round(latestRow.composite_score ?? 0)}</span>
          </span>
        )}
      </div>

      {/* Gauge row */}
      {latestRow && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
          <div className="card col-span-1 flex justify-center items-center">
            <ScoreGauge score={latestRow.composite_score} size={100} label="Composite" />
          </div>
          {INDICATOR_KEYS.map((k) => (
            <div key={k} className="card text-center">
              <p className="text-xs text-slate-400 mb-1">{INDICATOR_LABELS[k]}</p>
              <p className="text-2xl font-bold text-slate-100">
                {latestRow[k] != null ? Math.round(latestRow[k]!) : '—'}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Indicator trend */}
      <div className="card mb-4">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Indicator Trends</h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={indicatorTrendData} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {INDICATOR_KEYS.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} name={INDICATOR_LABELS[k]}
                stroke={Object.values(SIGNAL_COLORS)[i % 5]} dot={false} strokeWidth={2} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Signal trend */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Signal Hit Rates (%)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={signalTrend} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="bucket" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {signalKeys.map((k) => (
                <Line key={k} type="monotone" dataKey={k} name={signalLabels[k]}
                  stroke={SIGNAL_COLORS[k]} dot={false} strokeWidth={2} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Financials aggregate */}
        <FinancialsBarChart data={financials} title="Sector Financials Aggregate" />
      </div>

      {/* Companies */}
      <div className="card">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">
          Companies in {decoded} ({companies.length})
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {companies.map((c) => (
            <button
              key={`${c.company_code}-${c.exchange}`}
              onClick={() => navigate(`/companies/${c.company_code}`)}
              className="text-left p-3 bg-slate-700/50 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors"
            >
              <p className="font-semibold text-slate-200 text-sm truncate">{c.company_name ?? c.company_code}</p>
              <p className="text-xs text-slate-400 mt-0.5">{c.company_code} · {c.exchange}</p>
              <p className="text-xs text-slate-500 mt-0.5">{c.filing_count} filings</p>
            </button>
          ))}
          {companies.length === 0 && (
            <p className="col-span-full text-slate-400 text-sm">No companies found.</p>
          )}
        </div>
      </div>
    </div>
  )
}
