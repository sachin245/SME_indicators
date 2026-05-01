import { useData } from '../context/DataContext'
import { useFilters } from '../hooks/useFilters'

export default function GlobalFilterBar() {
  const { from, to, exchange, setFrom, setTo, toggleExchange } = useFilters()
  const { generatedAt } = useData()

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
      {generatedAt && (
        <span className="ml-auto text-xs text-slate-500">Data updated {generatedAt}</span>
      )}
    </div>
  )
}
