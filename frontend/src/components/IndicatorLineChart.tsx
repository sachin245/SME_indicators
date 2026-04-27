import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { IndicatorRow } from '../types'

const PALETTE = [
  '#6366f1', '#22c55e', '#f59e0b', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a78bfa',
]

interface Props {
  rows: IndicatorRow[]
  field?: keyof IndicatorRow
  title?: string
}

export default function IndicatorLineChart({
  rows,
  field = 'composite_score',
  title = 'Composite Score Trend',
}: Props) {
  if (!rows.length) {
    return (
      <div className="card flex items-center justify-center text-slate-400 h-48">
        No trend data yet.
      </div>
    )
  }

  // Pivot: [{date, SectorA: score, SectorB: score, ...}]
  const sectors = [...new Set(rows.map((r) => r.sector))]
  const dateMap = new Map<string, Record<string, unknown>>()

  for (const row of rows) {
    const entry = dateMap.get(row.as_of_date) ?? ({ date: row.as_of_date } as Record<string, unknown>)
    entry[row.sector] = row[field] as number | null
    dateMap.set(row.as_of_date, entry)
  }

  const data = [...dateMap.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  )

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-slate-300 mb-3">{title}</h2>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          {sectors.map((s, i) => (
            <Line
              key={s}
              type="monotone"
              dataKey={s}
              stroke={PALETTE[i % PALETTE.length]}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
