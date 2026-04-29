import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { fetchDataHealth } from '../api/health'

function daysAgo(iso: string | null): number | null {
  if (!iso) return null
  const d = new Date(iso.replace(' ', 'T'))
  if (isNaN(d.getTime())) return null
  return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24))
}

export default function DataHealthBanner() {
  const { data, isLoading } = useQuery({
    queryKey: ['data-health'],
    queryFn: fetchDataHealth,
    refetchInterval: 60_000,
  })

  if (isLoading || !data) return null

  const issues: string[] = []
  if (data.pdf_parse_coverage_pct < 25)
    issues.push(`Only ${data.pdf_parse_coverage_pct}% of filings have been parsed (${data.pdf_parsed.toLocaleString()} of ${data.total_filings.toLocaleString()})`)
  if (data.classified_sectors < 5)
    issues.push(`Only ${data.classified_sectors} sectors classified — indicator scores will be unreliable`)
  if (data.unclassified_signals > 0)
    issues.push(`${data.unclassified_signals.toLocaleString()} signals are still unclassified`)
  const stale = daysAgo(data.latest_filing)
  if (stale !== null && stale > 7)
    issues.push(`Latest filing is ${stale} days old — pipeline may be stalled`)
  const computeStale = daysAgo(data.last_compute)
  if (computeStale !== null && computeStale > 1)
    issues.push(`Indicators last computed ${computeStale}d ago`)

  if (issues.length === 0) {
    return (
      <div className="card flex items-center gap-3 mb-4 border border-emerald-700/40 bg-emerald-900/20">
        <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
        <div className="text-sm text-emerald-200">
          Data healthy — {data.total_filings.toLocaleString()} filings,{' '}
          {data.classified_sectors} sectors,{' '}
          {data.pdf_parse_coverage_pct}% parse coverage. Latest filing{' '}
          {data.latest_filing}.
        </div>
      </div>
    )
  }

  return (
    <div className="card flex items-start gap-3 mb-4 border border-amber-700/40 bg-amber-900/20">
      <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
      <div className="text-sm">
        <div className="font-semibold text-amber-200 mb-1">
          Data quality warnings ({issues.length})
        </div>
        <ul className="list-disc list-inside text-amber-100/90 space-y-0.5">
          {issues.map((i) => <li key={i}>{i}</li>)}
        </ul>
      </div>
    </div>
  )
}
