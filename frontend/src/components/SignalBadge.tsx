import clsx from 'clsx'

const SIGNAL_META: Record<string, { label: string; activeClass: string }> = {
  order_book:    { label: 'Order Book',    activeClass: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' },
  capex:         { label: 'Capex',         activeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  credit_stress: { label: 'Credit Stress', activeClass: 'bg-red-500/20 text-red-300 border-red-500/40' },
  export:        { label: 'Export',        activeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  headcount:     { label: 'Headcount',     activeClass: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' },
}

interface Props {
  signal: string
  active: boolean
  compact?: boolean
}

export default function SignalBadge({ signal, active, compact = false }: Props) {
  const meta = SIGNAL_META[signal]
  if (!meta) return null
  if (!active && compact) return null

  return (
    <span
      className={clsx(
        'badge border',
        active
          ? meta.activeClass
          : 'bg-slate-700/40 text-slate-500 border-slate-600/40'
      )}
    >
      {meta.label}
    </span>
  )
}

export function SignalBadgeRow({
  order_book, capex, credit_stress, export: exp, headcount, compact = false,
}: {
  order_book: boolean; capex: boolean; credit_stress: boolean
  export: boolean; headcount: boolean; compact?: boolean
}) {
  return (
    <div className="flex flex-wrap gap-1">
      <SignalBadge signal="order_book"    active={order_book}    compact={compact} />
      <SignalBadge signal="capex"         active={capex}         compact={compact} />
      <SignalBadge signal="credit_stress" active={credit_stress} compact={compact} />
      <SignalBadge signal="export"        active={exp}           compact={compact} />
      <SignalBadge signal="headcount"     active={headcount}     compact={compact} />
    </div>
  )
}
