import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import GlobalFilterBar from '../components/GlobalFilterBar'
import FinancialsBarChart from '../components/FinancialsBarChart'
import { SignalBadgeRow } from '../components/SignalBadge'
import { useFilters } from '../hooks/useFilters'
import { fetchFilings } from '../api/filings'
import { fetchFinancials } from '../api/financials'

export default function CompanyDetail() {
  const { code } = useParams<{ code: string }>()
  const navigate = useNavigate()
  const { from, to } = useFilters()
  const [page, setPage] = useState(0)
  const [periodType, setPeriodType] = useState<'Q' | 'A' | ''>('')
  const PAGE_SIZE = 25

  const { data: financials = [] } = useQuery({
    queryKey: ['financials', code, periodType],
    queryFn: () => fetchFinancials({
      company_code: code,
      period_type: periodType || undefined,
      limit: 40,
    }),
    enabled: !!code,
  })

  const { data: filingsRes, isLoading } = useQuery({
    queryKey: ['filings', 'company', code, from, to, page],
    queryFn: () => fetchFilings({
      company_code: code,
      from_date: from,
      to_date: to,
      page,
      page_size: PAGE_SIZE,
    }),
    enabled: !!code,
  })

  const filings = filingsRes?.data ?? []
  const total = filingsRes?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const company = filings[0] ?? financials[0]
  const companyName = (company as { company_name?: string | null })?.company_name ?? code
  const exchange = (company as { exchange?: string })?.exchange ?? ''

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

      {/* Financial chart */}
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
        <FinancialsBarChart
          data={[...financials].sort((a, b) => a.period_end.localeCompare(b.period_end))}
          title="Financial History"
        />
      </div>

      {/* Filings */}
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
              {isLoading && (
                <tr><td colSpan={5} className="text-center py-8 text-slate-400">Loading…</td></tr>
              )}
              {!isLoading && filings.length === 0 && (
                <tr><td colSpan={5} className="text-center py-8 text-slate-400">No filings found.</td></tr>
              )}
              {filings.map((f) => (
                <tr key={f.id} className="border-b border-slate-700/50 table-row-hover">
                  <td className="px-3 py-2 text-slate-400 whitespace-nowrap text-xs">{f.filing_date}</td>
                  <td className="px-3 py-2">
                    {f.category && (
                      <span className="badge bg-slate-600 text-slate-300">{f.category}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-300 max-w-xs">
                    <p className="truncate">{f.headline ?? '—'}</p>
                    {f.subcategory && (
                      <p className="text-xs text-slate-500 truncate">{f.subcategory}</p>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <SignalBadgeRow
                      order_book={f.order_book}
                      capex={f.capex}
                      credit_stress={f.credit_stress}
                      export={f.export}
                      headcount={f.headcount}
                      compact
                    />
                  </td>
                  <td className="px-3 py-2">
                    {f.pdf_url && (
                      <a
                        href={f.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-400 hover:text-indigo-300"
                        onClick={(e) => e.stopPropagation()}
                      >
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
