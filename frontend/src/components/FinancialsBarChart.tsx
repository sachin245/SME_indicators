import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts'
import type { Financial } from '../types'
import { fmtCrore } from '../utils/colors'

interface Props {
  data: Financial[]
  title?: string
}

export default function FinancialsBarChart({ data, title = 'Financials' }: Props) {
  if (!data.length) {
    return (
      <div className="card flex items-center justify-center text-slate-400 h-48">
        No financial data yet.
      </div>
    )
  }

  const sorted = [...data].sort((a, b) => a.period_end.localeCompare(b.period_end))

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-slate-300 mb-3">{title}</h2>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={sorted} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="period_end" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => fmtCrore(v)}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => fmtCrore(v)}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number) => fmtCrore(v)}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          <Bar yAxisId="left" dataKey="revenue" name="Revenue" fill="#6366f1" radius={[3,3,0,0]} />
          <Bar yAxisId="left" dataKey="ebitda" name="EBITDA" fill="#22c55e" radius={[3,3,0,0]} />
          <Bar yAxisId="left" dataKey="pat" name="PAT" fill="#f59e0b" radius={[3,3,0,0]} />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="total_debt"
            name="Debt"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
