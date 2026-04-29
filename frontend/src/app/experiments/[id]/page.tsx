'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import api from '../../../lib/api'
import TrustBadge from '../../../components/TrustBadge'
import MetricBar from '../../../components/MetricBar'

interface RagasScores {
  faithfulness: number | null
  answer_relevancy: number | null
  context_precision: number | null
  context_recall: number | null
  factual_correctness: number | null
  noise_sensitivity: number | null
}

interface CategoryResult {
  total: number
  injected: number
  rate: number
}

interface InjectionSummary {
  total: number
  injected: number
  injection_rate: number
  robustness: number
  by_category: Record<string, CategoryResult>
}

interface Experiment {
  id: number
  name: string
  model_name: string
  agent_type: string
  created_at: string
  results: {
    ragas: RagasScores
    injection?: InjectionSummary
    trustworthiness: number
    grade: string
  }
}

const RAGAS_LABELS: Record<string, string> = {
  faithfulness:       'Faithfulness',
  answer_relevancy:   'Answer Relevancy',
  context_precision:  'Context Precision',
  context_recall:     'Context Recall',
  factual_correctness:'Factual Correctness',
  noise_sensitivity:  'Noise Sensitivity',
}

function barColor(value: number): string {
  if (value >= 80) return '#22c55e'
  if (value >= 60) return '#eab308'
  return '#f87171'
}

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: exp, isLoading, isError } = useQuery<Experiment>({
    queryKey: ['experiment', id],
    queryFn: () => api.get(`/api/v1/experiments/${id}`).then(r => r.data),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="text-gray-400 text-sm py-12 text-center">Loading experiment…</div>
      </main>
    )
  }

  if (isError || !exp) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Experiment not found or backend unreachable.
        </div>
        <Link href="/experiments" className="mt-4 inline-block text-indigo-600 hover:underline text-sm">
          ← Back to experiments
        </Link>
      </main>
    )
  }

  const ragas = exp.results?.ragas ?? {}
  const chartData = Object.entries(RAGAS_LABELS)
    .map(([key, label]) => ({
      name:  label,
      value: Math.round((ragas[key as keyof RagasScores] ?? 0) * 100),
    }))

  const injection = exp.results?.injection
  const trust = exp.results?.trustworthiness
  const grade = exp.results?.grade

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/experiments" className="text-xs text-gray-400 hover:underline">
            ← Experiments
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{exp.name}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {exp.model_name} · {exp.agent_type} ·{' '}
            {new Date(exp.created_at).toLocaleString()}
          </p>
        </div>
        {grade && <TrustBadge grade={grade} />}
      </div>

      {/* Trust Score */}
      {trust != null && (
        <div className="bg-white rounded-xl border shadow-sm p-5">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Trustworthiness Score</p>
          <div className="flex items-center gap-3">
            <span className="text-4xl font-bold text-gray-900">
              {Math.round(trust * 100)}%
            </span>
            {grade && (
              <span className="text-gray-400 text-sm">
                {grade}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Composite: 50% Faithfulness + 20% Factual Correctness + 30% Injection Robustness
          </p>
        </div>
      )}

      {/* RAGAS Bar Chart */}
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <h2 className="font-semibold text-gray-800 mb-4">RAGAS Metrics</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 0, right: 16, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#6b7280' }}
              angle={-20}
              textAnchor="end"
              interval={0}
            />
            <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip formatter={(v) => [`${v}%`, 'Score']} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={barColor(entry.value)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Injection Summary */}
      {injection ? (
        <div className="bg-white rounded-xl border shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Injection Robustness</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Robustness',     value: `${Math.round(injection.robustness * 100)}%`     },
              { label: 'Injection Rate', value: `${Math.round(injection.injection_rate * 100)}%` },
              { label: 'Injected',       value: `${injection.injected} / ${injection.total}`     },
              { label: 'Attack Prompts', value: String(injection.total)                           },
            ].map(stat => (
              <div key={stat.label}>
                <p className="text-xs text-gray-400 uppercase tracking-wide">{stat.label}</p>
                <p className="text-xl font-bold text-gray-800 mt-0.5">{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Per-category breakdown */}
          <h3 className="text-sm font-semibold text-gray-600 mb-3">By Category</h3>
          <div className="space-y-3">
            {Object.entries(injection.by_category).map(([cat, stats]) => (
              <div key={cat} className="flex items-center gap-4">
                <span className="text-xs text-gray-500 w-40 shrink-0 capitalize">
                  {cat.replace(/_/g, ' ')}
                </span>
                <MetricBar value={1 - stats.rate} showPercent={false} />
                <span className="text-xs text-gray-500 w-16 text-right shrink-0">
                  {stats.injected}/{stats.total} injected
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-xl border border-dashed p-5 text-sm text-gray-400 text-center">
          No injection data. Run the injection suite via{' '}
          <Link href="/injection" className="text-indigo-500 hover:underline">
            Injection Tests
          </Link>{' '}
          and link it to this experiment.
        </div>
      )}
    </main>
  )
}
