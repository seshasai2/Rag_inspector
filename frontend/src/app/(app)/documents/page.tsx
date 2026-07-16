'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

interface DocRow {
  id: string
  title: string
  freshness_status: string
  days_since_modified?: number
  source_url?: string
  chunk_count: number
}

export default function DocumentsFreshnessPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [title, setTitle] = useState('')
  const queryClient = useQueryClient()

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['documents', pipelineId],
    queryFn: () =>
      api
        .get('/documents', {
          params: { pipeline_id: pipelineId || undefined, per_page: 50 },
        })
        .then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: () =>
      api
        .post('/documents', {
          pipeline_id: pipelineId,
          title,
          last_modified_at: new Date().toISOString(),
        })
        .then((r) => r.data),
    onSuccess: () => {
      toast.success('Document registered')
      setTitle('')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: () => toast.error('Select a pipeline and title'),
  })

  const items: DocRow[] = data?.items ?? []

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Documents"
        description="Track knowledge-base documents and freshness (daily Celery check)."
      />

      <div className="flex flex-wrap gap-2 mb-6">
        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
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
        <input
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm min-w-[220px]"
          placeholder="Document title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button
          type="button"
          className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground disabled:opacity-40"
          disabled={!pipelineId || !title.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          Add document
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <Panel variant="solid" title="No documents">
          <p className="text-sm text-muted-foreground">
            Register documents you care about for stale detection. Beat runs
            <code className="mx-1">check_document_freshness</code> daily.
          </p>
        </Panel>
      ) : (
        <div className="space-y-2">
          {items.map((doc) => (
            <div key={doc.id} className="rounded-xl border border-border bg-card p-4 flex gap-3">
              <FileText size={16} className="mt-1 text-muted-foreground shrink-0" />
              <div>
                <p className="font-medium text-sm">{doc.title}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.freshness_status}
                  {doc.days_since_modified != null ? ` · ${doc.days_since_modified}d` : ''}
                  {` · ${doc.chunk_count} chunks`}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
