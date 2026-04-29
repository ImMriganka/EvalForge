interface StatCardProps {
  label: string
  value: string | number
  colorClass?: string
}

export default function StatCard({
  label,
  value,
  colorClass = 'bg-indigo-50 text-indigo-700',
}: StatCardProps) {
  return (
    <div className={`rounded-xl p-5 shadow-sm ${colorClass}`}>
      <p className="text-xs uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  )
}
