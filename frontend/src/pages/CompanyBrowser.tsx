import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'
import GlobalFilterBar from '../components/GlobalFilterBar'
import { useFilters } from '../hooks/useFilters'
import { fetchCompanies } from '../api/filings'
import { fetchSectors } from '../api/indicators'

export default function CompanyBrowser() {
  const navigate = useNavigate()
  const { exchange } = useFilters()
  const [search, setSearch] = useState('')
  const [sector, setSector] = useState('')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 50

  const params = {
    exchange: exchange.length ? exchange : undefined,
    sector: sector || undefined,
    search: search || undefined,
    page,
    page_size: PAGE_SIZE,
  }

  const { data: result, isLoading } = useQuery({
    queryKey: ['companies', params],
    queryFn: () => fetchCompanies(params),
  })

  const { data: sectors = [] } = useQuery({
    queryKey: ['sectors'],
    queryFn: fetchSectors,
  })

  const companies = result?.data ?? []
  const total = result?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  function handleSearch(val: string) {
    setSearch(val)
    setPage(0)
  }
  function handleSector(val: string) {
    setSector(val)
    setPage(0)
  }

  return (
    <div>
      <GlobalFilterBar />
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <h1 className="text-lg font-bold text-slate-100 mr-2">Companies</h1>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-8 w-56"
            placeholder="Search name or code…"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
        <select
          className="input"
          value={sector}
          onChange={(e) => handleSector(e.target.value)}
        >
          <option value="">All sectors</option>
          {sectors.map((s) => (
            <option key={s.sector} value={s.sector}>{s.sector}</option>
          ))}
        </select>
        <span className="text-sm text-slate-400 ml-auto">
          {total.toLocaleString()} companies
        </span>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left px-3 py-2 text-slate-400 font-medium">Company</th>
              <th className="text-left px-3 py-2 text-slate-400 font-medium">Code</th>
              <th className="text-left px-3 py-2 text-slate-400 font-medium">Exchange</th>
              <th className="text-left px-3 py-2 text-slate-400 font-medium">Sector</th>
              <th className="text-right px-3 py-2 text-slate-400 font-medium">Filings</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="text-center py-8 text-slate-400">Loading…</td>
              </tr>
            )}
            {!isLoading && companies.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center py-8 text-slate-400">No companies found.</td>
              </tr>
            )}
            {companies.map((c) => (
              <tr
                key={`${c.company_code}-${c.exchange}`}
                onClick={() => navigate(`/companies/${c.company_code}`)}
                className="border-b border-slate-700/50 cursor-pointer table-row-hover"
              >
                <td className="px-3 py-2 text-slate-200 font-medium">
                  {c.company_name ?? '—'}
                </td>
                <td className="px-3 py-2 text-slate-400 font-mono text-xs">{c.company_code}</td>
                <td className="px-3 py-2">
                  <span className={`badge ${c.exchange === 'BSE' ? 'bg-blue-500/20 text-blue-300' : 'bg-purple-500/20 text-purple-300'}`}>
                    {c.exchange}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-400">{c.sector}</td>
                <td className="px-3 py-2 text-right text-slate-400">{c.filing_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-slate-400">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              className="btn-ghost"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft size={15} /> Prev
            </button>
            <button
              className="btn-ghost"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
