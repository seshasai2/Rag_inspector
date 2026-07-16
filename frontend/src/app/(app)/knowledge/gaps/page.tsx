'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

interface KnowledgeGap {
  id: string
  pipeline_id: string
  topic_label: string
  representative_query?: string
  query_count: number
  failure_rate?: number
  estimated_monthly_cost_usd?: number
  priority: string
  suggested_document_topic?: string
  status: string
  updated_at: string
}

const STATUSES = ['open', 'acknowledged', 'in_progress', 'fixed'] as const

export default function KnowledgeGapsPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [status, setStatus] = useState('open')
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge-gaps', pipelineId, status, page],
    queryFn: () =>
      api
        .get('/knowledge/gaps', {
          params: {
            page,
            per_page: 20,
            pipeline_id: pipelineId || undefined,
            status: status || undefined,
          },
        })
        .then((r) => r.data),
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, next }: { id: string; next: string }) =>
      api.patch(`/knowledge/gaps/${id}`, { status: next }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-gaps'] })
      toast.success('Gap status updated')
    },
    onError: () => toast.error('Failed to update status'),
  })

  const items: KnowledgeGap[] = data?.items ?? []
  const totalCost = items.reduce((sum, g) => sum + (g.estimated_monthly_cost_usd ?? 0), 0)

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Knowledge gaps"
        description="Clustered coverage gaps from failed retrieval queries (HDBSCAN / keyword fallback)."
      />

      <div className="flex flex-wrap gap-3 mb-6">
        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
          value={pipelineId}
          onChange={(e) => {
            setPipelineId(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All pipelines</option>
          {(pipelines ?? []).map((p: { id: string; name: string }) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <div className="text-sm text-muted-foreground self-center">
          Est. monthly impact (page): ${totalCost.toFixed(0)}
        </div>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading gaps…</p>
      ) : items.length === 0 ? (
        <Panel variant="solid" title="No gaps yet">
          <p className="text-sm text-muted-foreground">
            Gaps appear after analysis finds enough <code>coverage_gap</code> queries to cluster
            (default min cluster size 3). Seed a demo or send failing traces via the SDK.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3">
          {items.map((gap) => (
            <div
              key={gap.id}
              className="rounded-xl border border-border bg-card p-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle size={16} className="text-amber-500 shrink-0" />
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">
                    {gap.priority} · {gap.status}
                  </span>
                  <span className="text-xs text-muted-foreground">{gap.query_count} queries</span>
                </div>
                <p className="font-medium text-foreground break-words">{gap.topic_label}</p>
                {gap.suggested_document_topic && (
                  <p className="text-sm text-muted-foreground mt-1">{gap.suggested_document_topic}</p>
                )}
                {gap.estimated_monthly_cost_usd != null && (
                  <p className="text-xs text-muted-foreground mt-2">
                    ~${gap.estimated_monthly_cost_usd.toFixed(0)}/mo estimated impact
                  </p>
                )}
              </div>
              <select
                className="bg-background border border-border rounded-lg px-3 py-2 text-sm shrink-0"
                value={gap.status}
                disabled={updateStatus.isPending}
                onChange={(e) => updateStatus.mutate({ id: gap.id, next: e.target.value })}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="flex gap-2 mt-6">
          <button
            type="button"
            className="px-3 py-1.5 text-sm border border-border rounded-lg disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Prev
          </button>
          <span className="text-sm text-muted-foreground self-center">
            Page {page} / {data.pages}
          </span>
          <button
            type="button"
            className="px-3 py-1.5 text-sm border border-border rounded-lg disabled:opacity-40"
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
