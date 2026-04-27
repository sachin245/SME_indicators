import { scoreTextClass } from '../utils/colors'

interface Props {
  score: number | null
  size?: number
  label?: string
}

export default function ScoreGauge({ score, size = 140, label = 'Composite Score' }: Props) {
  const cx = size / 2
  const cy = size * 0.58
  const r = size * 0.38
  const strokeW = size * 0.085

  // arc from left (180°) to right (0°), going clockwise over top
  const startX = cx - r
  const startY = cy
  const endX = cx + r
  const endY = cy

  function arcPoint(score: number) {
    const capped = Math.min(score, 99.9)
    const angleDeg = 180 - capped * 1.8
    const rad = (angleDeg * Math.PI) / 180
    return {
      x: cx + r * Math.cos(rad),
      y: cy - r * Math.sin(rad),
      largeArc: capped > 50 ? 1 : 0,
    }
  }

  const bg = `M ${startX} ${startY} A ${r} ${r} 0 0 1 ${endX} ${endY}`

  let fgPath = ''
  const textClass = scoreTextClass(score)

  if (score != null && score > 0) {
    const { x, y, largeArc } = arcPoint(score)
    fgPath = `M ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${x} ${y}`
  }

  const fillColor =
    score == null ? '#475569'
    : score >= 66 ? '#22c55e'
    : score >= 33 ? '#f59e0b'
    : '#ef4444'

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        <path
          d={bg}
          fill="none"
          stroke="#334155"
          strokeWidth={strokeW}
          strokeLinecap="round"
        />
        {fgPath && (
          <path
            d={fgPath}
            fill="none"
            stroke={fillColor}
            strokeWidth={strokeW}
            strokeLinecap="round"
          />
        )}
        <text
          x={cx}
          y={cy + strokeW * 0.3}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.22}
          fontWeight="700"
          fill={fillColor}
        >
          {score != null ? Math.round(score) : '—'}
        </text>
        <text
          x={cx}
          y={cy + strokeW * 0.3 + size * 0.17}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.09}
          fill="#94a3b8"
        >
          / 100
        </text>
      </svg>
      <span className={`text-sm font-medium ${textClass}`}>{label}</span>
    </div>
  )
}
