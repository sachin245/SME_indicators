import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import GlobalFilterBar from '../components/GlobalFilterBar'
import FinancialsBarChart from '../components/FinancialsBarChart'
import ScoreGauge from '../components/ScoreGauge'
import { useFilters } from '../hooks/useFilters'
import { useData } from '../context/DataContext'
import { INDICATOR_LABELS, SIGNAL_COLORS } from '../utils/colors'

const INDICATOR_KEYS = [
  'revenue_momentum', 'margin_pressure', 'order_book_signal',
  'credit_stress', 'capex_intentions', 'export_outlook',
] as const

const SIGNAL_KEYS = ['order_book_rate', 'capex_rate', 'credit_stress_rate', 'export_rate', 'headcount_rate']
const SIGNAL_LABELS: Record<string, string> = {
  order_book_rate: 'Order Book', capex_rate: 'Capex',
  credit_stress_rate: 'Credit Stress', export_rate: 'Export', headcount_rate: 'Headcount',
}

export default function SectorDetail() {
  const { sector } = useParams<{ sector: string }>()
  const navigate = useNavigate()
  const { from, to, exchange } = useFilters()
  const decoded = decodeURIComponent(sector ?? '')

  const { indicatorsLatest, indicatorHistory, companies, financials, signalTrend } = useData()

  const latestRow = useMemo(
    () => indicatorsLatest.find((r) => r.sector === decoded),
    [indicatorsLatest, decoded],
  )

  const history = useMemo(
    () => indicatorHistory.filter(
      (r) => r.sector === decoded && r.as_of_date >= from && r.as_of_date <= to,
    ),
    [indicatorHistory, decoded, from, to],
  )

  const sectorCompanies = useMemo(
    () => companies.filter(
      (c) => c.sector === decoded && (exchange.length === 0 || exchange.includes(c.exchange)),
    ),
    [companies, decoded, exchange],
  )

  const sectorFinancials = useMemo(
    () => financials.filter(
      (f) => f.sector === decoded && f.period_end >= from && f.period_end <= to,
    ),
    [financials, decoded, from, to],
  )

  const sectorSignalTrend = useMemo(
    () => signalTrend.filter((r) => r.bucket >= from && r.bucket <= to),
    [signalTrend, from, to],
  )

  const indicatorTrendData = history.map((r) => ({
    date: r.as_of_date,
    ...INDICATOR_KEYS.reduce((acc, k) => ({ ...acc, [k]: r[k] }), {}),
  }))

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
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Signal Hit Rates (%)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={sectorSignalTrend} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="bucket" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {SIGNAL_KEYS.map((k) => (
                <Line key={k} type="monotone" dataKey={k} name={SIGNAL_LABELS[k]}
                  stroke={SIGNAL_COLORS[k]} dot={false} strokeWidth={2} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <FinancialsBarChart data={sectorFinancials} title="Sector Financials Aggregate" />
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">
          Companies in {decoded} ({sectorCompanies.length})
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {sectorCompanies.map((c) => (
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
          {sectorCompanies.length === 0 && (
            <p className="col-span-full text-slate-400 text-sm">No companies found.</p>
          )}
        </div>
      </div>
    </div>
  )
}
