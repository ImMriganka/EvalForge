'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import api from '../lib/api'
import StatCard from '../components/StatCard'

interface RagasScores {
  faithfulness: number | null
  answer_relevancy: number | null
  context_precision: number | null
  context_recall: number | null
  factual_correctness: number | null
  noise_sensitivity: number | null
}

interface Experiment {
  id: number
  name: string
  model_name: string
  agent_type: string
  created_at: string
  results: {
    ragas: RagasScores
    injection?: { injection_rate: number; robustness: number }
    trustworthiness: number
    grade: string
  }
}

function avg(values: (number | null | undefined)[]): number | null {
  const nums = values.filter((v): v is number => v != null && !isNaN(v))
  if (nums.length === 0) return null
  return nums.reduce((a, b) => a + b, 0) / nums.length
}

function fmt(value: number | null, asPercent = true): string {
  if (value == null) return '—'
  return asPercent ? `${Math.round(value * 100)}%` : value.toFixed(2)
}

export default function DashboardPage() {
  const { data: experiments, isLoading, isError } = useQuery<Experiment[]>({
    queryKey: ['experiments'],
    queryFn: () => api.get('/api/v1/experiments').then(r => r.data),
  })

  const totalExperiments = experiments?.length ?? 0
  const avgFaithfulness  = avg(experiments?.map(e => e.results?.ragas?.faithfulness) ?? [])
  const avgTrust         = avg(experiments?.map(e => e.results?.trustworthiness) ?? [])
  const avgInjectionRate = avg(experiments?.map(e => e.results?.injection?.injection_rate ?? 0) ?? [])

  const kpis = [
    { label: 'Experiments',      value: isLoading ? '…' : String(totalExperiments), colorClass: 'bg-indigo-50 text-indigo-700' },
    { label: 'Avg Faithfulness', value: isLoading ? '…' : fmt(avgFaithfulness),     colorClass: 'bg-green-50 text-green-700'  },
    { label: 'Avg Trust Score',  value: isLoading ? '…' : fmt(avgTrust),            colorClass: 'bg-blue-50 text-blue-700'    },
    { label: 'Avg Injection Rate', value: isLoading ? '…' : fmt(avgInjectionRate),  colorClass: 'bg-red-50 text-red-700'      },
  ]

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500 text-sm">
          LLM Agent Benchmarking &amp; Trustworthiness Platform
        </p>
      </div>

      {isError && (
        <div className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Could not reach the backend. Make sure the FastAPI server is running on{' '}
          <code className="bg-red-100 px-1 rounded">http://localhost:8000</code>.
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {kpis.map(kpi => (
          <StatCard key={kpi.label} label={kpi.label} value={kpi.value} colorClass={kpi.colorClass} />
        ))}
      </div>

      {/* Navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { href: '/experiments', title: 'Experiments',    desc: 'Browse and compare all evaluation runs',      icon: '🧪' },
          { href: '/injection',   title: 'Injection Tests', desc: 'Run the 6-category prompt injection suite',   icon: '🔐' },
        ].map(link => (
          <Link
            key={link.href}
            href={link.href}
            className="block rounded-xl border bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="text-2xl mb-2">{link.icon}</div>
            <h2 className="font-semibold text-gray-800">{link.title}</h2>
            <p className="mt-1 text-sm text-gray-500">{link.desc}</p>
          </Link>
        ))}
      </div>
    </main>
  )
}
