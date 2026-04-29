interface TrustBadgeProps {
  grade: string
}

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800',
  B: 'bg-yellow-100 text-yellow-800',
  C: 'bg-orange-100 text-orange-800',
  D: 'bg-red-100 text-red-800',
}

export default function TrustBadge({ grade }: TrustBadgeProps) {
  const letter = grade?.[0] ?? '?'
  const colorClass = GRADE_COLORS[letter] ?? 'bg-gray-100 text-gray-700'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${colorClass}`}
    >
      <span className="text-base font-bold">{letter}</span>
      <span className="opacity-80 font-normal text-xs">{grade?.slice(4)}</span>
    </span>
  )
}
