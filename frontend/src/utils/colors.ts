/** Map a 0–100 score to a CSS HSL colour (red → amber → green). */
export function scoreToHsl(score: number | null | undefined): string {
  if (score == null) return 'hsl(220, 15%, 35%)'
  const clamped = Math.max(0, Math.min(100, score))
  const hue = clamped * 1.2          // 0 → 0° (red), 100 → 120° (green)
  return `hsl(${hue}, 70%, 42%)`
}

/** Return a Tailwind text class based on score band. */
export function scoreTextClass(score: number | null | undefined): string {
  if (score == null) return 'text-slate-400'
  if (score >= 66) return 'text-emerald-400'
  if (score >= 33) return 'text-amber-400'
  return 'text-red-400'
}

/** Format a number as ₹ crores with suffix. */
export function fmtCrore(val: number | null | undefined): string {
  if (val == null) return '—'
  if (Math.abs(val) >= 1e7) return `₹${(val / 1e7).toFixed(1)}Cr`
  if (Math.abs(val) >= 1e5) return `₹${(val / 1e5).toFixed(1)}L`
  return `₹${val.toFixed(0)}`
}

export const INDICATOR_LABELS: Record<string, string> = {
  revenue_momentum: 'Revenue',
  margin_pressure: 'Margin',
  order_book_signal: 'Order Book',
  credit_stress: 'Credit',
  capex_intentions: 'Capex',
  export_outlook: 'Export',
}

export const SIGNAL_COLORS: Record<string, string> = {
  order_book_rate: '#6366f1',
  capex_rate: '#22c55e',
  credit_stress_rate: '#ef4444',
  export_rate: '#f59e0b',
  headcount_rate: '#06b6d4',
}
