'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import api from '../../lib/api'
import MetricBar from '../../components/MetricBar'

interface CategoryResult {
  total: number
  injected: number
  rate: number
}

interface InjectionResult {
  summary: {
    total: number
    injected: number
    injection_rate: number
    robustness: number
    by_category: Record<string, CategoryResult>
  }
  details: Record<string, Array<{ prompt: string; response: string; injected: boolean }>>
}

const CATEGORY_LABELS: Record<string, string> = {
  direct_override:    'Direct Override',
  roleplay_jailbreak: 'Roleplay Jailbreak',
  indirect_tool:      'Indirect Tool',
  code_injection:     'Code Injection',
  encoding_tricks:    'Encoding Tricks',
  context_overflow:   'Context Overflow',
}

export default function InjectionPage() {
  const [modelName, setModelName] = useState('llama3.1:8b')
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)

  const { mutate, data, isPending, isError, error, isSuccess, reset } = useMutation<
    InjectionResult,
    AxiosError,
    string
  >({
    mutationFn: (model: string) =>
      api.post('/api/v1/injection/run', { model_name: model }).then(r => r.data),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    reset()
    mutate(modelName)
  }

  const errorDetail = (() => {
    if (!isError) return null
    const status = error?.response?.status
    if (status === 503) {
      return 'Cannot reach Ollama. Make sure it is running: ollama serve'
    }
    const msg = (error?.response?.data as { detail?: string })?.detail
    return msg ?? error?.message ?? 'Unexpected error'
  })()

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Injection Test Suite</h1>
      <p className="text-sm text-gray-500 mb-8">
        Runs 13 adversarial prompts across 6 attack categories against your Ollama model.
      </p>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border shadow-sm p-5 mb-8 flex gap-3 items-end">
        <div className="flex-1">
          <label htmlFor="model" className="block text-xs font-medium text-gray-600 mb-1">
            Model name
          </label>
          <input
            id="model"
            type="text"
            value={modelName}
            onChange={e => setModelName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="llama3.1:8b"
            disabled={isPending}
          />
        </div>
        <button
          type="submit"
          disabled={isPending || !modelName.trim()}
          className="rounded-lg bg-indigo-600 text-white px-5 py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Running…' : 'Run Injection Suite'}
        </button>
      </form>

      {/* Loading state */}
      {isPending && (
        <div className="text-center py-12 text-gray-500 space-y-3">
          <div className="inline-block w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          <p className="text-sm">
            Running 13 attack prompts against{' '}
            <span className="font-mono font-semibold">{modelName}</span>…
          </p>
          <p className="text-xs text-gray-400">This may take 1–3 minutes</p>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {errorDetail}
        </div>
      )}

      {/* Results */}
      {isSuccess && data && (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                label: 'Robustness',
                value: `${Math.round(data.summary.robustness * 100)}%`,
                color: data.summary.robustness >= 0.8 ? 'bg-green-50 text-green-700' : data.summary.robustness >= 0.6 ? 'bg-yellow-50 text-yellow-700' : 'bg-red-50 text-red-700',
              },
              {
                label: 'Injection Rate',
                value: `${Math.round(data.summary.injection_rate * 100)}%`,
                color: 'bg-red-50 text-red-700',
              },
              {
                label: 'Injected',
                value: `${data.summary.injected} / ${data.summary.total}`,
                color: 'bg-gray-50 text-gray-700',
              },
              {
                label: 'Prompts Tested',
                value: String(data.summary.total),
                color: 'bg-indigo-50 text-indigo-700',
              },
            ].map(s => (
              <div key={s.label} className={`rounded-xl p-4 shadow-sm ${s.color}`}>
                <p className="text-xs uppercase tracking-wide opacity-70">{s.label}</p>
                <p className="text-2xl font-bold mt-1">{s.value}</p>
              </div>
            ))}
          </div>

          {/* Per-category breakdown */}
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <h2 className="font-semibold text-gray-800 mb-4">Category Breakdown</h2>
            <div className="space-y-4">
              {Object.entries(data.summary.by_category).map(([cat, stats]) => (
                <div key={cat}>
                  <div className="flex items-center gap-3 cursor-pointer"
                    onClick={() => setExpandedCategory(expandedCategory === cat ? null : cat)}>
                    <span className="text-sm font-medium text-gray-700 w-44 shrink-0">
                      {CATEGORY_LABELS[cat] ?? cat}
                    </span>
                    <MetricBar value={1 - stats.rate} showPercent={false} />
                    <span className="text-xs text-gray-500 w-20 text-right shrink-0">
                      {stats.injected}/{stats.total} injected
                    </span>
                    <span className="text-gray-400 text-xs shrink-0">
                      {expandedCategory === cat ? '▲' : '▼'}
                    </span>
                  </div>

                  {/* Expanded prompt details */}
                  {expandedCategory === cat && data.details[cat] && (
                    <div className="mt-3 ml-4 space-y-3">
                      {data.details[cat].map((item, i) => (
                        <div
                          key={i}
                          className={`rounded-lg p-3 text-xs border ${
                            item.injected
                              ? 'bg-red-50 border-red-200'
                              : 'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1.5">
                            <span
                              className={`rounded-full px-2 py-0.5 font-semibold text-xs ${
                                item.injected ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'
                              }`}
                            >
                              {item.injected ? 'INJECTED' : 'SAFE'}
                            </span>
                          </div>
                          <p className="text-gray-500 mb-1">
                            <span className="font-semibold text-gray-700">Prompt: </span>
                            {item.prompt}
                          </p>
                          <p className="text-gray-500">
                            <span className="font-semibold text-gray-700">Response: </span>
                            {item.response}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
