import { useMemo } from 'react'
import { Building2, FileText, TrendingUp } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import GlobalFilterBar from '../components/GlobalFilterBar'
import ScoreGauge from '../components/ScoreGauge'
import SectorHeatmap from '../components/SectorHeatmap'
import IndicatorLineChart from '../components/IndicatorLineChart'
import { useFilters } from '../hooks/useFilters'
import { useData } from '../context/DataContext'
import { scoreToHsl } from '../utils/colors'

function KpiCard({ label, value, icon: Icon, sub }: {
  label: string; value: string | number; icon: React.ElementType; sub?: string
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className="p-2.5 bg-indigo-600/20 rounded-lg">
        <Icon size={20} className="text-indigo-400" />
      </div>
      <div>
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-2xl font-bold text-slate-100">{value}</p>
        {sub && <p className="text-xs text-slate-500">{sub}</p>}
      </div>
    </div>
  )
}

export default function Overview() {
  const { from, to } = useFilters()
  const { indicatorsLatest, indicatorHistory, summary } = useData()

  const sortedLatest = useMemo(
    () => [...indicatorsLatest].sort((a, b) => (b.composite_score ?? 0) - (a.composite_score ?? 0)),
    [indicatorsLatest],
  )

  const history = useMemo(
    () => indicatorHistory.filter((r) => r.as_of_date >= from && r.as_of_date <= to),
    [indicatorHistory, from, to],
  )

  const sc = summary?.signal_counts
  const signalItems = [
    { label: 'Order Book', value: sc?.order_book ?? 0 },
    { label: 'Capex', value: sc?.capex ?? 0 },
    { label: 'Credit Stress', value: sc?.credit_stress ?? 0 },
    { label: 'Export', value: sc?.export ?? 0 },
    { label: 'Headcount', value: sc?.headcount ?? 0 },
  ]

  return (
    <div>
      <GlobalFilterBar />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card flex flex-col items-center justify-center py-4">
          <ScoreGauge score={summary?.composite_score ?? null} size={120} />
        </div>
        <KpiCard
          label="Total Filings"
          value={(summary?.total_filings ?? 0).toLocaleString()}
          icon={FileText}
          sub="in dataset"
        />
        <KpiCard
          label="Companies Tracked"
          value={(summary?.total_companies ?? 0).toLocaleString()}
          icon={Building2}
        />
        <div className="card">
          <p className="text-xs text-slate-400 mb-2">Signal Counts</p>
          <div className="flex flex-col gap-1">
            {signalItems.map(({ label, value }) => (
              <div key={label} className="flex justify-between text-sm">
                <span className="text-slate-400">{label}</span>
                <span className="font-semibold text-slate-200">{value.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mb-6">
        <SectorHeatmap rows={indicatorsLatest} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} className="text-indigo-400" />
            <h2 className="text-sm font-semibold text-slate-300">Current Composite Score</h2>
          </div>
          {sortedLatest.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={sortedLatest}
                layout="vertical"
                margin={{ top: 0, right: 12, bottom: 0, left: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
                <YAxis type="category" dataKey="sector" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} width={80} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  formatter={(v: number) => [Math.round(v), 'Score']}
                />
                <Bar dataKey="composite_score" radius={[0, 4, 4, 0]}>
                  {sortedLatest.map((row) => (
                    <Cell key={row.sector} fill={scoreToHsl(row.composite_score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
              No data — export from Streamlit first.
            </div>
          )}
        </div>

        <IndicatorLineChart rows={history} title="Composite Score Over Time" />
      </div>
    </div>
  )
}
