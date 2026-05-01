import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import GlobalFilterBar from '../components/GlobalFilterBar'
import FinancialsBarChart from '../components/FinancialsBarChart'
import { SignalBadgeRow } from '../components/SignalBadge'
import { useFilters } from '../hooks/useFilters'
import { useData } from '../context/DataContext'

const PAGE_SIZE = 25

export default function CompanyDetail() {
  const { code } = useParams<{ code: string }>()
  const navigate = useNavigate()
  const { from, to } = useFilters()
  const { filings, financials } = useData()
  const [page, setPage] = useState(0)
  const [periodType, setPeriodType] = useState<'Q' | 'A' | ''>('')

  const companyFinancials = useMemo(
    () => financials
      .filter((f) => f.company_code === code && (!periodType || f.period_type === periodType))
      .sort((a, b) => a.period_end.localeCompare(b.period_end)),
    [financials, code, periodType],
  )

  const companyFilings = useMemo(
    () => filings.filter(
      (f) => f.company_code === code && f.filing_date >= from && f.filing_date <= to,
    ),
    [filings, code, from, to],
  )

  const total = companyFilings.length
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const paginated = companyFilings.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const first = companyFilings[0] ?? companyFinancials[0]
  const companyName = (first as { company_name?: string | null })?.company_name ?? code
  const exchange = (first as { exchange?: string })?.exchange ?? ''

  return (
    <div>
      <GlobalFilterBar />
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(-1)} className="btn-ghost">
          <ArrowLeft size={15} /> Back
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-100">{companyName}</h1>
          <p className="text-sm text-slate-400">{code} · {exchange}</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm text-slate-400">Period type:</span>
          {(['', 'Q', 'A'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setPeriodType(t)}
              className={`px-3 py-1 rounded-lg text-xs font-medium border transition-colors ${
                periodType === t
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-slate-700 border-slate-600 text-slate-400 hover:text-slate-200'
              }`}
            >
              {t === '' ? 'All' : t === 'Q' ? 'Quarterly' : 'Annual'}
            </button>
          ))}
        </div>
        <FinancialsBarChart data={companyFinancials} title="Financial History" />
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">
          Filings ({total.toLocaleString()})
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left px-3 py-2 text-slate-400 font-medium">Date</th>
                <th className="text-left px-3 py-2 text-slate-400 font-medium">Category</th>
                <th className="text-left px-3 py-2 text-slate-400 font-medium">Headline</th>
                <th className="text-left px-3 py-2 text-slate-400 font-medium">Signals</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 && (
                <tr><td colSpan={5} className="text-center py-8 text-slate-400">No filings found.</td></tr>
              )}
              {paginated.map((f) => (
                <tr key={f.id} className="border-b border-slate-700/50 table-row-hover">
                  <td className="px-3 py-2 text-slate-400 whitespace-nowrap text-xs">{f.filing_date}</td>
                  <td className="px-3 py-2">
                    {f.category && <span className="badge bg-slate-600 text-slate-300">{f.category}</span>}
                  </td>
                  <td className="px-3 py-2 text-slate-300 max-w-xs">
                    <p className="truncate">{f.headline ?? '—'}</p>
                    {f.subcategory && <p className="text-xs text-slate-500 truncate">{f.subcategory}</p>}
                  </td>
                  <td className="px-3 py-2">
                    <SignalBadgeRow
                      order_book={f.order_book} capex={f.capex}
                      credit_stress={f.credit_stress} export={f.export}
                      headcount={f.headcount} compact
                    />
                  </td>
                  <td className="px-3 py-2">
                    {f.pdf_url && (
                      <a href={f.pdf_url} target="_blank" rel="noopener noreferrer"
                        className="text-indigo-400 hover:text-indigo-300"
                        onClick={(e) => e.stopPropagation()}>
                        <ExternalLink size={14} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-slate-400">Page {page + 1} of {totalPages}</span>
            <div className="flex gap-2">
              <button className="btn-ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft size={15} /> Prev
              </button>
              <button className="btn-ghost" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
