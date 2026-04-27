import { useNavigate } from 'react-router-dom'
import type { IndicatorRow } from '../types'
import { scoreToHsl, INDICATOR_LABELS } from '../utils/colors'

const INDICATOR_KEYS = [
  'revenue_momentum',
  'margin_pressure',
  'order_book_signal',
  'credit_stress',
  'capex_intentions',
  'export_outlook',
] as const

interface Props {
  rows: IndicatorRow[]
}

export default function SectorHeatmap({ rows }: Props) {
  const navigate = useNavigate()

  if (!rows.length) {
    return (
      <div className="card text-center text-slate-400 py-10">
        No indicator data yet — run the pipeline to compute indicators.
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <h2 className="text-sm font-semibold text-slate-300 mb-3">Sector Heatmap</h2>
      <table className="w-full text-sm border-separate border-spacing-0.5">
        <thead>
          <tr>
            <th className="text-left px-2 py-1.5 text-slate-400 font-medium min-w-[140px]">
              Sector
            </th>
            {INDICATOR_KEYS.map((k) => (
              <th key={k} className="px-2 py-1.5 text-slate-400 font-medium whitespace-nowrap">
                {INDICATOR_LABELS[k]}
              </th>
            ))}
            <th className="px-2 py-1.5 text-slate-400 font-medium">Composite</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.sector}
              onClick={() => navigate(`/sectors/${encodeURIComponent(row.sector)}`)}
              className="cursor-pointer group"
            >
              <td className="px-2 py-1.5 text-slate-200 group-hover:text-indigo-300 transition-colors font-medium rounded-l">
                {row.sector}
              </td>
              {INDICATOR_KEYS.map((k) => {
                const val = row[k]
                return (
                  <td
                    key={k}
                    className="px-2 py-1.5 text-center text-white font-semibold rounded"
                    style={{ backgroundColor: scoreToHsl(val) }}
                  >
                    {val != null ? Math.round(val) : '—'}
                  </td>
                )
              })}
              <td
                className="px-2 py-1.5 text-center text-white font-bold rounded-r"
                style={{ backgroundColor: scoreToHsl(row.composite_score) }}
              >
                {row.composite_score != null ? Math.round(row.composite_score) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
