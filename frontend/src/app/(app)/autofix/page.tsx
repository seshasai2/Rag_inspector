'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Wrench } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

interface FixRec {
  id: string
  recommendation_type: string
  topic_description: string
  affected_query_count: number
  status: string
  trust_score_before?: number
  trust_score_after?: number
}

export default function AutofixPage() {
  const [status, setStatus] = useState('open')
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['autofix', status],
    queryFn: () =>
      api
        .get('/autofix/recommendations', {
          params: { status: status || undefined, per_page: 50 },
        })
        .then((r) => r.data),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['autofix'] })

  const apply = useMutation({
    mutationFn: (id: string) => api.post(`/autofix/recommendations/${id}/apply`).then((r) => r.data),
    onSuccess: () => {
      toast.success('Marked applied (KB change is still on you)')
      invalidate()
    },
  })
  const dismiss = useMutation({
    mutationFn: (id: string) => api.post(`/autofix/recommendations/${id}/dismiss`).then((r) => r.data),
    onSuccess: () => {
      toast.success('Dismissed')
      invalidate()
    },
  })
  const verify = useMutation({
    mutationFn: (id: string) => api.post(`/autofix/recommendations/${id}/verify`).then((r) => r.data),
    onSuccess: (res) => {
      const delta = res.trust_delta
      toast.success(
        delta == null
          ? 'Trust score recorded'
          : `Trust ${res.trust_score_after} (Δ ${delta > 0 ? '+' : ''}${delta})`,
      )
      invalidate()
    },
    onError: () => toast.error('Verify requires applied status'),
  })

  const items: FixRec[] = data?.items ?? []

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Fix recommendations"
        description="Apply or dismiss analysis suggestions, then verify Trust Score after you update your knowledge base."
      />
      <select
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm mb-6"
        value={status}
        onChange={(e) => setStatus(e.target.value)}
      >
        <option value="open">open</option>
        <option value="applied">applied</option>
        <option value="dismissed">dismissed</option>
        <option value="">all</option>
      </select>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <Panel variant="solid" title="No recommendations">
          <p className="text-sm text-muted-foreground">
            Recommendations appear when analysis clusters coverage gaps or retrieval issues.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3">
          {items.map((rec) => (
            <div key={rec.id} className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Wrench size={14} />
                <span>{rec.recommendation_type}</span>
                <span>·</span>
                <span>{rec.status}</span>
                <span>·</span>
                <span>{rec.affected_query_count} queries</span>
              </div>
              <p className="text-sm text-foreground mb-3">{rec.topic_description}</p>
              {(rec.trust_score_before != null || rec.trust_score_after != null) && (
                <p className="text-xs text-muted-foreground mb-3">
                  Trust before: {rec.trust_score_before ?? '—'} · after: {rec.trust_score_after ?? '—'}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {rec.status === 'open' && (
                  <>
                    <button
                      type="button"
                      className="px-3 py-1.5 text-sm rounded-lg bg-primary text-primary-foreground"
                      onClick={() => apply.mutate(rec.id)}
                    >
                      Apply
                    </button>
                    <button
                      type="button"
                      className="px-3 py-1.5 text-sm rounded-lg border border-border"
                      onClick={() => dismiss.mutate(rec.id)}
                    >
                      Dismiss
                    </button>
                  </>
                )}
                {rec.status === 'applied' && (
                  <button
                    type="button"
                    className="px-3 py-1.5 text-sm rounded-lg border border-border"
                    onClick={() => verify.mutate(rec.id)}
                  >
                    Verify Trust Score
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
