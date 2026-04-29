'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import api from '../../lib/api'
import TrustBadge from '../../components/TrustBadge'

interface Experiment {
  id: number
  name: string
  model_name: string
  agent_type: string
  created_at: string
  results: {
    ragas: Record<string, number | null>
    injection?: { injection_rate: number; robustness: number }
    trustworthiness: number
    grade: string
  }
}

export default function ExperimentsPage() {
  const { data: experiments, isLoading, isError } = useQuery<Experiment[]>({
    queryKey: ['experiments'],
    queryFn: () => api.get('/api/v1/experiments').then(r => r.data),
  })

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Experiments</h1>

      {isLoading && (
        <div className="text-gray-500 text-sm py-8 text-center">Loading experiments…</div>
      )}

      {isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Could not reach backend at{' '}
          <code className="bg-red-100 px-1 rounded">http://localhost:8000</code>.
        </div>
      )}

      {!isLoading && !isError && experiments?.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No experiments yet.</p>
          <p className="text-sm mt-1">Run an evaluation via the API to get started.</p>
        </div>
      )}

      {experiments && experiments.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Name', 'Model', 'Agent', 'Grade', 'Trust', 'Created', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {experiments.map(exp => (
                <tr key={exp.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{exp.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{exp.model_name}</td>
                  <td className="px-4 py-3 text-gray-500">{exp.agent_type}</td>
                  <td className="px-4 py-3">
                    {exp.results?.grade
                      ? <TrustBadge grade={exp.results.grade} />
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {exp.results?.trustworthiness != null
                      ? `${Math.round(exp.results.trustworthiness * 100)}%`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(exp.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/experiments/${exp.id}`}
                      className="text-indigo-600 hover:underline text-xs font-medium"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
