interface MetricBarProps {
  value: number   // 0–1
  label?: string
  showPercent?: boolean
}

export default function MetricBar({ value, label, showPercent = true }: MetricBarProps) {
  const pct = Math.round(value * 100)

  let barColor = 'bg-green-500'
  if (pct < 60) barColor = 'bg-red-400'
  else if (pct < 80) barColor = 'bg-yellow-400'

  return (
    <div className="flex items-center gap-2 w-full">
      {label && <span className="text-xs text-gray-500 w-24 shrink-0">{label}</span>}
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showPercent && (
        <span className="text-xs text-gray-600 w-9 text-right shrink-0">{pct}%</span>
      )}
    </div>
  )
}
