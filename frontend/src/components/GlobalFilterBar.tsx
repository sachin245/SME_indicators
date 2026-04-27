import { useEffect, useRef } from 'react'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import { useFilters } from '../hooks/useFilters'
import { apiFetch } from '../api/client'

type PipelineStatus = { status: 'idle' | 'running' | 'error'; message: string }

export default function GlobalFilterBar() {
  const { from, to, exchange, setFrom, setTo, toggleExchange } = useFilters()
  const queryClient = useQueryClient()
  const wasRunning = useRef(false)

  const { data: pipeline, refetch: pollStatus } = useQuery<PipelineStatus>({
    queryKey: ['pipeline', 'status'],
    queryFn: () => apiFetch('/api/pipeline/status'),
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 2000 : false,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (wasRunning.current && pipeline?.status !== 'running') {
      queryClient.invalidateQueries()
    }
    wasRunning.current = pipeline?.status === 'running'
  }, [pipeline?.status, queryClient])

  async function handleFetch() {
    await apiFetch('/api/pipeline/run', undefined, 'POST')
    pollStatus()
  }

  const isRunning = pipeline?.status === 'running'
  const isError = pipeline?.status === 'error'

  return (
    <div className="flex flex-wrap items-center gap-4 mb-6 p-3 bg-slate-800 border border-slate-700 rounded-xl">
      <div className="flex items-center gap-2 text-sm">
        <label className="text-slate-400 whitespace-nowrap">From</label>
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="input"
        />
      </div>
      <div className="flex items-center gap-2 text-sm">
        <label className="text-slate-400 whitespace-nowrap">To</label>
        <input
          type="date"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="input"
        />
      </div>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-400">Exchange</span>
        {['BSE', 'NSE'].map((ex) => (
          <button
            key={ex}
            onClick={() => toggleExchange(ex)}
            className={`px-3 py-1 rounded-lg text-xs font-medium border transition-colors ${
              exchange.includes(ex) || exchange.length === 0
                ? 'bg-indigo-600 border-indigo-500 text-white'
                : 'bg-slate-700 border-slate-600 text-slate-400 hover:text-slate-200'
            }`}
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        {pipeline?.message && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            {isError && <AlertCircle size={12} className="text-red-400" />}
            {!isRunning && !isError && pipeline.message.startsWith('Done') && (
              <CheckCircle size={12} className="text-emerald-400" />
            )}
            {pipeline.message}
          </span>
        )}
        <button
          onClick={handleFetch}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-indigo-500 bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw size={13} className={isRunning ? 'animate-spin' : ''} />
          {isRunning ? 'Running…' : 'Fetch Data'}
        </button>
      </div>
    </div>
  )
}
