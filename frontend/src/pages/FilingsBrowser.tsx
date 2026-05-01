import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, Filter, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import GlobalFilterBar from '../components/GlobalFilterBar'
import { SignalBadgeRow } from '../components/SignalBadge'
import { useFilters } from '../hooks/useFilters'
import { useData } from '../context/DataContext'

const PAGE_SIZE = 50

const SIGNAL_OPTIONS = [
  { key: 'order_book',    label: 'Order Book' },
  { key: 'capex',         label: 'Capex' },
  { key: 'credit_stress', label: 'Credit Stress' },
  { key: 'export',        label: 'Export' },
  { key: 'headcount',     label: 'Headcount' },
]

export default function FilingsBrowser() {
  const navigate = useNavigate()
  const { from, to, exchange } = useFilters()
  const { filings, sectors, categories } = useData()
  const [sector, setSector] = useState('')
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [signals, setSignals] = useState<string[]>([])
  const [page, setPage] = useState(0)
  const [showFilters, setShowFilters] = useState(true)

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return filings.filter((f) => {
      if (f.filing_date < from || f.filing_date > to) return false
      if (exchange.length > 0 && !exchange.includes(f.exchange)) return false
      if (sector && f.sector !== sector) return false
      if (category && f.category !== category) return false
      if (q && !f.company_code.toLowerCase().includes(q) && !(f.company_name ?? '').toLowerCase().includes(q)) return false
      if (signals.length > 0 && !signals.some((s) => (f as unknown as Record<string, unknown>)[s])) return false
      return true
    })
  }, [filings, from, to, exchange, sector, category, search, signals])

  const total = filtered.length
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function toggleSignal(key: string) {
    setSignals((prev) => prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key])
    setPage(0)
  }
  function resetFilters() {
    setSector(''); setCategory(''); setSearch(''); setSignals([]); setPage(0)
  }

  return (
    <div>
      <GlobalFilterBar />
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-lg font-bold text-slate-100">Filings Browser</h1>
        <span className="text-sm text-slate-400 ml-1">{total.toLocaleString()} results</span>
        <button className="btn-ghost ml-auto" onClick={() => setShowFilters((v) => !v)}>
          <Filter size={14} /> Filters
        </button>
      </div>

      <div className="flex gap-4">
        {showFilters && (
          <aside className="w-56 shrink-0 space-y-4">
            <div className="card space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Company search</label>
                <div className="relative">
                  <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    className="input pl-7 w-full"
                    placeholder="Code or name…"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(0) }}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Sector</label>
                <select className="input w-full" value={sector} onChange={(e) => { setSector(e.target.value); setPage(0) }}>
                  <option value="">All sectors</option>
                  {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Category</label>
                <select className="input w-full" value={category} onChange={(e) => { setCategory(e.target.value); setPage(0) }}>
                  <option value="">All categories</option>
                  {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Signals (any of)</label>
                <div className="flex flex-col gap-1.5">
                  {SIGNAL_OPTIONS.map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={signals.includes(key)}
                        onChange={() => toggleSignal(key)}
                        className="accent-indigo-500 w-3.5 h-3.5"
                      />
                      <span className="text-sm text-slate-300">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button className="btn-ghost w-full text-xs" onClick={resetFilters}>Reset filters</button>
            </div>
          </aside>
        )}

        <div className="flex-1 min-w-0">
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left px-3 py-2 text-slate-400 font-medium whitespace-nowrap">Date</th>
                  <th className="text-left px-3 py-2 text-slate-400 font-medium">Exchange</th>
                  <th className="text-left px-3 py-2 text-slate-400 font-medium">Company</th>
                  <th className="text-left px-3 py-2 text-slate-400 font-medium">Category</th>
                  <th className="text-left px-3 py-2 text-slate-400 font-medium">Headline</th>
                  <th className="text-left px-3 py-2 text-slate-400 font-medium">Signals</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {paginated.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-10 text-slate-400">No filings match the current filters.</td></tr>
                )}
                {paginated.map((f) => (
                  <tr key={f.id} className="border-b border-slate-700/50 table-row-hover">
                    <td className="px-3 py-2 text-slate-400 text-xs whitespace-nowrap">{f.filing_date}</td>
                    <td className="px-3 py-2">
                      <span className={`badge ${f.exchange === 'BSE' ? 'bg-blue-500/20 text-blue-300' : 'bg-purple-500/20 text-purple-300'}`}>
                        {f.exchange}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <button
                        className="text-slate-200 hover:text-indigo-300 text-left transition-colors"
                        onClick={() => navigate(`/companies/${f.company_code}`)}
                      >
                        <span className="block font-medium truncate max-w-[120px]">{f.company_name ?? f.company_code}</span>
                        <span className="text-xs text-slate-500">{f.company_code}</span>
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      {f.category && <span className="badge bg-slate-600 text-slate-300">{f.category}</span>}
                    </td>
                    <td className="px-3 py-2 text-slate-300 max-w-xs">
                      <p className="truncate text-sm">{f.headline ?? '—'}</p>
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
                          className="text-indigo-400 hover:text-indigo-300">
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
              <span className="text-sm text-slate-400">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()}
              </span>
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
    </div>
  )
}
