'use client'
import { useState, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import api from '@/lib/api'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'

function ScoreBadge({ score }: { score?: number | null }) {
  if (score == null) return <span className="text-xs text-muted-foreground">—</span>
  const pct = (score * 100).toFixed(0)
  const cls = score >= 0.7 ? 'text-green-600 bg-green-50' : score >= 0.5 ? 'text-amber-600 bg-amber-50' : 'text-red-600 bg-red-50'
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{pct}%</span>
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: 'text-slate-500 bg-slate-100',
    analyzing: 'text-blue-600 bg-blue-50 animate-pulse',
    completed: 'text-green-600 bg-green-50',
    failed: 'text-red-600 bg-red-50',
  }
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${map[status] || 'text-slate-500'}`}>{status}</span>
}

function FailureTypeBadge({ type }: { type?: string | null }) {
  if (!type || type === 'none') return null
  const map: Record<string, string> = {
    hallucination: 'text-red-600 bg-red-50',
    retrieval_miss: 'text-amber-600 bg-amber-50',
    retrieval_irrelevant: 'text-orange-600 bg-orange-50',
    coverage_gap: 'text-purple-600 bg-purple-50',
    chunking_issue: 'text-cyan-600 bg-cyan-50',
  }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${map[type] || 'text-slate-500 bg-slate-100'}`}>
      {type.replace(/_/g, ' ')}
    </span>
  )
}

function QueriesContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [page, setPage] = useState(1)
  const [failureFilter, setFailureFilter] = useState(searchParams.get('failure_type') || '')
  const [hallucinationFilter, setHallucinationFilter] = useState(searchParams.get('is_hallucination') || '')
  const [pipelineFilter, setPipelineFilter] = useState(searchParams.get('pipeline_id') || '')
  const [sortBy, setSortBy] = useState('traced_at')
  const [sortOrder, setSortOrder] = useState('desc')

  const syncUrl = (next: { failure?: string; hall?: string; pipeline?: string }) => {
    const params = new URLSearchParams()
    const f = next.failure ?? failureFilter
    const h = next.hall ?? hallucinationFilter
    const p = next.pipeline ?? pipelineFilter
    if (f) params.set('failure_type', f)
    if (h) params.set('is_hallucination', h)
    if (p) params.set('pipeline_id', p)
    const qs = params.toString()
    router.replace(qs ? `/queries?${qs}` : '/queries')
  }

  const { data, isLoading } = useQuery({
    queryKey: ['queries', page, failureFilter, hallucinationFilter, pipelineFilter, sortBy, sortOrder],
    queryFn: () => api.get('/queries', {
      params: {
        page, per_page: 25,
        failure_type: failureFilter || undefined,
        pipeline_id: pipelineFilter || undefined,
        is_hallucination: hallucinationFilter === 'true' ? true : hallucinationFilter === 'false' ? false : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
    }).then(r => r.data),
  })

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then(r => r.data),
  })

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Query Traces</h1>
          <p className="text-muted-foreground text-sm mt-1">{data?.total?.toLocaleString() ?? '—'} total traces</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={pipelineFilter}
          onChange={(e) => { setPipelineFilter(e.target.value); setPage(1); syncUrl({ pipeline: e.target.value }) }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All pipelines</option>
          {pipelines?.map((p: { id: string; name: string }) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>

        <select
          value={failureFilter}
          onChange={(e) => { setFailureFilter(e.target.value); setPage(1); syncUrl({ failure: e.target.value }) }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All failure types</option>
          <option value="hallucination">Hallucination</option>
          <option value="retrieval_miss">Retrieval Miss</option>
          <option value="retrieval_irrelevant">Retrieval Irrelevant</option>
          <option value="coverage_gap">Coverage Gap</option>
          <option value="chunking_issue">Chunking Issue</option>
          <option value="none">No failure</option>
        </select>

        <select
          value={hallucinationFilter}
          onChange={(e) => { setHallucinationFilter(e.target.value); setPage(1); syncUrl({ hall: e.target.value }) }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All queries</option>
          <option value="true">Hallucinations only</option>
          <option value="false">Grounded only</option>
        </select>

        <select
          value={`${sortBy}_${sortOrder}`}
          onChange={(e) => {
            const [sb, so] = e.target.value.split('_')
            setSortBy(sb); setSortOrder(so); setPage(1)
          }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="traced_at_desc">Newest first</option>
          <option value="traced_at_asc">Oldest first</option>
          <option value="faithfulness_asc">Worst faithfulness</option>
          <option value="faithfulness_desc">Best faithfulness</option>
        </select>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Query</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Pipeline</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Faithfulness</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Grounded</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Failure</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array(10).fill(0).map((_, i) => (
                <tr key={i}>
                  {Array(7).fill(0).map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="skeleton h-4 rounded" /></td>
                  ))}
                </tr>
              ))
            ) : !data?.items?.length ? (
              <tr>
                <td colSpan={7} className="text-center py-16 text-muted-foreground">
                  <Search className="mx-auto mb-3 opacity-30" size={32} />
                  <p>No traces found. Integrate the SDK to start seeing queries.</p>
                </td>
              </tr>
            ) : (
              data.items.map((trace: {
                id: string; query_text: string; pipeline_name?: string;
                faithfulness_score?: number; grounded_fraction?: number;
                failure_type?: string; analysis_status: string; traced_at: string;
              }) => (
                <tr key={trace.id} className="hover:bg-muted/20 transition-colors group">
                  <td className="px-4 py-3 max-w-xs">
                    <Link href={`/queries/${trace.id}`} className="text-sm text-foreground group-hover:text-primary transition-colors line-clamp-1">
                      {trace.query_text}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-muted-foreground">{trace.pipeline_name || '—'}</span>
                  </td>
                  <td className="px-4 py-3"><ScoreBadge score={trace.faithfulness_score} /></td>
                  <td className="px-4 py-3"><ScoreBadge score={trace.grounded_fraction} /></td>
                  <td className="px-4 py-3"><FailureTypeBadge type={trace.failure_type} /></td>
                  <td className="px-4 py-3"><StatusBadge status={trace.analysis_status} /></td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-muted-foreground">
                      {new Date(trace.traced_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {data && data.pages > 1 && (
          <div className="px-4 py-3 border-t border-border flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.page} of {data.pages} · {data.total.toLocaleString()} results
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
                className="p-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function QueriesPage() {
  return (
    <Suspense fallback={<div className="p-6 text-muted-foreground">Loading queries…</div>}>
      <QueriesContent />
    </Suspense>
  )
}
