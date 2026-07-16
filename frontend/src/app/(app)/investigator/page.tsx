'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

export default function InvestigatorPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [question, setQuestion] = useState('What is my trust score and hallucination rate?')
  const [answer, setAnswer] = useState<{
    answer: string
    citations: Array<{ metric: string; value: unknown }>
    mode: string
  } | null>(null)

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const ask = useMutation({
    mutationFn: () =>
      api
        .post('/investigator/ask', {
          question,
          pipeline_id: pipelineId || undefined,
        })
        .then((r) => r.data),
    onSuccess: setAnswer,
    onError: () => toast.error('Pro plan required'),
  })

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <PageHeader
        title="AI Investigator"
        description="Ask questions over real dashboard metrics — answers include citations."
      />
      <select
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm mb-3 w-full"
        value={pipelineId}
        onChange={(e) => setPipelineId(e.target.value)}
      >
        <option value="">All pipelines</option>
        {(pipelines ?? []).map((p: { id: string; name: string }) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <textarea
        className="w-full min-h-[100px] bg-card border border-border rounded-lg p-3 text-sm mb-3"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button
        type="button"
        className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground mb-6"
        onClick={() => ask.mutate()}
      >
        Ask
      </button>
      {answer && (
        <Panel variant="solid" title={`Answer (${answer.mode})`}>
          <p className="text-sm mb-4">{answer.answer}</p>
          <ul className="text-xs text-muted-foreground space-y-1">
            {(answer.citations || []).map((c, i) => (
              <li key={`${c.metric}-${i}`}>
                {c.metric}: {String(c.value)}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  )
}
