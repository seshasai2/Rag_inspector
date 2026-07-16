'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

export default function BenchmarkPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [retrieval, setRetrieval] = useState<Record<string, unknown> | null>(null)
  const [llm, setLlm] = useState<Record<string, unknown> | null>(null)

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const runRetrieval = useMutation({
    mutationFn: () => api.post(`/benchmark/retrieval/${pipelineId}`).then((r) => r.data),
    onSuccess: (data) => {
      setRetrieval(data)
      toast.success('Retrieval benchmark complete')
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail || 'Failed (Pro plan)'),
  })

  const runLlm = useMutation({
    mutationFn: () => api.post(`/benchmark/llm/${pipelineId}`).then((r) => r.data),
    onSuccess: (data) => {
      setLlm(data)
      toast.success('LLM comparison complete')
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail || 'Failed (Pro plan)'),
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Benchmark"
        description="BM25 vs vector on real traces, plus faithfulness bucket comparison (no synthetic scores)."
      />
      <select
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm mb-4"
        value={pipelineId}
        onChange={(e) => setPipelineId(e.target.value)}
      >
        <option value="">Select pipeline</option>
        {(pipelines ?? []).map((p: { id: string; name: string }) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <div className="flex gap-2 mb-6">
        <button
          type="button"
          disabled={!pipelineId}
          className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground disabled:opacity-40"
          onClick={() => runRetrieval.mutate()}
        >
          Run retrieval benchmark
        </button>
        <button
          type="button"
          disabled={!pipelineId}
          className="px-3 py-2 text-sm rounded-lg border border-border disabled:opacity-40"
          onClick={() => runLlm.mutate()}
        >
          Run LLM comparison
        </button>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Panel variant="solid" title="Retrieval">
          <pre className="text-xs overflow-auto max-h-96">{JSON.stringify(retrieval, null, 2) || '—'}</pre>
        </Panel>
        <Panel variant="solid" title="LLM buckets">
          <pre className="text-xs overflow-auto max-h-96">{JSON.stringify(llm, null, 2) || '—'}</pre>
        </Panel>
      </div>
    </div>
  )
}
