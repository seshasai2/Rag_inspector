'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

export default function StudioPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [prompt, setPrompt] = useState(
    'You are a helpful assistant. Use the context to answer. Cite sources.',
  )
  const [promptResult, setPromptResult] = useState<Record<string, unknown> | null>(null)
  const [chunkResult, setChunkResult] = useState<Record<string, unknown> | null>(null)

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const analyze = useMutation({
    mutationFn: () => api.post('/studio/prompt/analyze', { prompt_text: prompt }).then((r) => r.data),
    onSuccess: setPromptResult,
    onError: () => toast.error('Pro plan required'),
  })

  const optimize = useMutation({
    mutationFn: () => api.get(`/studio/chunks/optimize/${pipelineId}`).then((r) => r.data),
    onSuccess: setChunkResult,
    onError: () => toast.error('Failed'),
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Studio"
        description="Prompt analyzer and chunk optimizer from measured stats — no fake predictions."
      />
      <div className="grid lg:grid-cols-2 gap-6">
        <Panel variant="solid" title="Prompt analyzer">
          <textarea
            className="w-full min-h-[140px] bg-background border border-border rounded-lg p-3 text-sm mb-3"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <button
            type="button"
            className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground"
            onClick={() => analyze.mutate()}
          >
            Analyze
          </button>
          <pre className="text-xs mt-3 overflow-auto max-h-64">{JSON.stringify(promptResult, null, 2)}</pre>
        </Panel>
        <Panel variant="solid" title="Chunk optimizer">
          <select
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm mb-3 w-full"
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
          <button
            type="button"
            disabled={!pipelineId}
            className="px-3 py-2 text-sm rounded-lg border border-border disabled:opacity-40"
            onClick={() => optimize.mutate()}
          >
            Suggest chunk actions
          </button>
          <pre className="text-xs mt-3 overflow-auto max-h-64">{JSON.stringify(chunkResult, null, 2)}</pre>
        </Panel>
      </div>
    </div>
  )
}
