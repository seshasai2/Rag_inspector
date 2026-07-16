'use client'
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { Flag, Search, Database, LayoutGrid, List } from 'lucide-react'
import { usePipelineId, usePipelines } from '@/hooks/usePipelineId'
import { ErrorState } from '@/components/app-shell'
import { getApiErrorMessage } from '@/lib/errors'

interface ChunkStat {
  id: string; chunk_id: string; pipeline_id: string; text: string;
  retrieval_count: number; citation_count: number; citation_rate: number;
  is_flagged: boolean; last_retrieved_at?: string;
}

const LOW_QUALITY_MIN_RETRIEVALS = 50
const LOW_QUALITY_MAX_RATE = 0.2

function heatColor(rate: number): string {
  // Dark green (high citation) → dark red (low citation)
  if (rate >= 0.8) return 'bg-emerald-700 text-white'
  if (rate >= 0.6) return 'bg-emerald-500 text-white'
  if (rate >= 0.4) return 'bg-amber-400 text-slate-900'
  if (rate >= 0.2) return 'bg-orange-500 text-white'
  return 'bg-red-700 text-white'
}

function heatBg(rate: number): string {
  if (rate >= 0.8) return 'bg-emerald-700/90 border-emerald-800'
  if (rate >= 0.6) return 'bg-emerald-500/90 border-emerald-600'
  if (rate >= 0.4) return 'bg-amber-400/90 border-amber-500'
  if (rate >= 0.2) return 'bg-orange-500/90 border-orange-600'
  return 'bg-red-700/90 border-red-800'
}

function isAutoFlagEligible(chunk: ChunkStat): boolean {
  return chunk.retrieval_count >= LOW_QUALITY_MIN_RETRIEVALS && chunk.citation_rate < LOW_QUALITY_MAX_RATE
}

function CitationHeatCell({ rate }: { rate: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-sm ${heatColor(rate).split(' ')[0]}`} title={`Citation rate: ${(rate * 100).toFixed(0)}%`} />
      <span className="text-xs font-medium tabular-nums">{(rate * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function ChunksPage() {
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('retrieval_count')
  const [search, setSearch] = useState('')
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const { pipelineId, setPipelineId } = usePipelineId()
  const { data: pipelines } = usePipelines()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [view, setView] = useState<'heatmap' | 'table'>('heatmap')

  const queryClient = useQueryClient()

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['chunks', page, sortBy, search, flaggedOnly, pipelineId, view],
    queryFn: () => api.get('/chunks', {
      params: {
        page,
        per_page: view === 'heatmap' ? 96 : 25,
        sort_by: sortBy,
        sort_order: 'desc',
        search: search || undefined,
        flagged_only: flaggedOnly || undefined,
        pipeline_id: pipelineId || undefined,
      },
    }).then(r => r.data),
  })

  const { data: summary } = useQuery({
    queryKey: ['chunks-summary', pipelineId],
    queryFn: () => api.get('/chunks/summary', {
      params: { pipeline_id: pipelineId || undefined },
    }).then(r => r.data),
  })

  const flagMutation = useMutation({
    mutationFn: ({ chunkId, pipelineId }: { chunkId: string; pipelineId: string }) =>
      api.post(`/chunks/${chunkId}/flag`, null, { params: { pipeline_id: pipelineId } }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chunks'] })
      queryClient.invalidateQueries({ queryKey: ['chunks-summary'] })
      toast.success('Chunk flag updated')
    },
  })

  const heatCells = useMemo<ChunkStat[]>(() => data?.items ?? [], [data?.items])

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Chunk Quality Heatmap</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Citation rate colors each chunk — dark green (high quality) to dark red (retrieved but rarely cited).
            Auto-flag: {LOW_QUALITY_MIN_RETRIEVALS}+ retrievals and &lt;{(LOW_QUALITY_MAX_RATE * 100).toFixed(0)}% citation.
          </p>
        </div>
        <div className="flex rounded-lg border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => { setView('heatmap'); setPage(1) }}
            className={`px-3 py-2 text-sm flex items-center gap-1.5 ${view === 'heatmap' ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground'}`}
          >
            <LayoutGrid size={14} /> Heatmap
          </button>
          <button
            type="button"
            onClick={() => { setView('table'); setPage(1) }}
            className={`px-3 py-2 text-sm flex items-center gap-1.5 ${view === 'table' ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground'}`}
          >
            <List size={14} /> Table
          </button>
        </div>
      </div>

      {/* Summary + legend */}
      <div className="grid md:grid-cols-4 gap-3 mb-6">
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground">Tracked chunks</p>
          <p className="text-2xl font-bold text-foreground mt-1">{summary?.total_chunks ?? '—'}</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground">Avg citation rate</p>
          <p className="text-2xl font-bold text-foreground mt-1">
            {summary ? `${(summary.avg_citation_rate * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground">Flagged</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{summary?.flagged_count ?? '—'}</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground">Auto-flag eligible</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{summary?.low_quality_eligible ?? '—'}</p>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-4 mb-6 flex items-center gap-6 flex-wrap">
        <span className="text-sm font-medium text-muted-foreground">Citation Rate:</span>
        {[
          { label: '80–100%', color: 'bg-emerald-700', desc: 'Excellent' },
          { label: '60–79%', color: 'bg-emerald-500', desc: 'Good' },
          { label: '40–59%', color: 'bg-amber-400', desc: 'Fair' },
          { label: '20–39%', color: 'bg-orange-500', desc: 'Poor' },
          { label: '0–19%', color: 'bg-red-700', desc: 'Low quality' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded-sm ${item.color}`} />
            <span className="text-xs text-muted-foreground">{item.label} ({item.desc})</span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search chunk text..."
            className="w-full pl-8 pr-4 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <select
          value={pipelineId || ''}
          onChange={(e) => { setPipelineId(e.target.value || undefined); setPage(1) }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All pipelines</option>
          {pipelines?.map((p: { id: string; name: string }) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={(e) => { setSortBy(e.target.value); setPage(1) }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="retrieval_count">Sort: Most retrieved</option>
          <option value="citation_rate">Sort: Citation rate</option>
          <option value="citation_count">Sort: Citation count</option>
          <option value="last_retrieved_at">Sort: Recently retrieved</option>
        </select>
        <label className="flex items-center gap-2 cursor-pointer bg-card border border-border rounded-lg px-3 py-2">
          <input type="checkbox" checked={flaggedOnly} onChange={(e) => { setFlaggedOnly(e.target.checked); setPage(1) }} />
          <span className="text-sm text-foreground">Flagged only</span>
        </label>
      </div>

      {isError && (
        <ErrorState
          message={getApiErrorMessage(error, 'Failed to load chunks.')}
          onRetry={() => refetch()}
          title="Chunks unavailable"
        />
      )}

      {view === 'heatmap' ? (
        <div className="bg-card border border-border rounded-xl p-4">
          {isLoading ? (
            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12 gap-2">
              {Array(24).fill(0).map((_, i) => <div key={i} className="skeleton aspect-square rounded-lg" />)}
            </div>
          ) : !heatCells.length ? (
            <div className="text-center py-16 text-muted-foreground">
              <Database className="mx-auto mb-3 opacity-30" size={32} />
              <p>No chunks tracked yet. Send traces to start monitoring chunk quality.</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12 gap-2">
              {heatCells.map((chunk) => {
                const eligible = isAutoFlagEligible(chunk)
                return (
                  <button
                    key={chunk.id}
                    type="button"
                    title={`${(chunk.citation_rate * 100).toFixed(0)}% cited · ${chunk.retrieval_count} retrievals\n${chunk.text.slice(0, 120)}`}
                    onClick={() => setExpandedId(expandedId === chunk.id ? null : chunk.id)}
                    className={`relative aspect-square rounded-lg border p-1.5 text-left transition-transform hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${heatBg(chunk.citation_rate)} ${
                      chunk.is_flagged ? 'ring-2 ring-amber-300' : ''
                    }`}
                  >
                    <span className="text-[10px] font-bold leading-none block">
                      {(chunk.citation_rate * 100).toFixed(0)}%
                    </span>
                    <span className="text-[9px] opacity-80 block mt-0.5">{chunk.retrieval_count}×</span>
                    {(chunk.is_flagged || eligible) && (
                      <Flag size={10} className="absolute top-1 right-1 opacity-90" />
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {expandedId && (
            <div className="mt-4 border border-border rounded-xl p-4 bg-muted/20">
              {(() => {
                const chunk = heatCells.find((c) => c.id === expandedId)
                if (!chunk) return null
                return (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${heatColor(chunk.citation_rate)}`}>
                        {(chunk.citation_rate * 100).toFixed(0)}% citation
                      </span>
                      <span className="text-xs text-muted-foreground">{chunk.retrieval_count} retrievals · {chunk.citation_count} cited</span>
                      {chunk.is_flagged && (
                        <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">Flagged</span>
                      )}
                      {isAutoFlagEligible(chunk) && (
                        <span className="text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded-full">
                          Auto-flag rule (50+ / &lt;20%)
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => flagMutation.mutate({ chunkId: chunk.chunk_id, pipelineId: chunk.pipeline_id })}
                        className="ml-auto text-xs px-3 py-1.5 rounded-lg border border-border hover:bg-muted"
                      >
                        {chunk.is_flagged ? 'Unflag' : 'Flag for review'}
                      </button>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
                    <p className="text-xs font-mono text-muted-foreground">{chunk.chunk_id}</p>
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Chunk Text</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Citation Rate</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Retrieved</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Cited</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Last Retrieved</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase">Flag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                Array(10).fill(0).map((_, i) => (
                  <tr key={i}>{Array(6).fill(0).map((_, j) => <td key={j} className="px-4 py-3"><div className="skeleton h-4 rounded" /></td>)}</tr>
                ))
              ) : !heatCells.length ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-muted-foreground">
                    <Database className="mx-auto mb-3 opacity-30" size={32} />
                    <p>No chunks tracked yet. Send traces to start monitoring chunk quality.</p>
                  </td>
                </tr>
              ) : (
                heatCells.map((chunk) => (
                  <tr
                    key={chunk.id}
                    className={`hover:bg-muted/20 cursor-pointer transition-colors ${chunk.is_flagged ? 'bg-amber-50/30' : ''}`}
                    onClick={() => setExpandedId(expandedId === chunk.id ? null : chunk.id)}
                  >
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-sm text-foreground line-clamp-1">{chunk.text}</p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">{chunk.chunk_id.slice(0, 20)}...</p>
                      {isAutoFlagEligible(chunk) && (
                        <span className="text-[10px] text-red-600 font-medium">Auto-flag eligible</span>
                      )}
                    </td>
                    <td className="px-4 py-3"><CitationHeatCell rate={chunk.citation_rate} /></td>
                    <td className="px-4 py-3"><span className="text-sm font-medium tabular-nums">{chunk.retrieval_count.toLocaleString()}</span></td>
                    <td className="px-4 py-3"><span className="text-sm tabular-nums">{chunk.citation_count.toLocaleString()}</span></td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted-foreground">
                        {chunk.last_retrieved_at ? new Date(chunk.last_retrieved_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          flagMutation.mutate({ chunkId: chunk.chunk_id, pipelineId: chunk.pipeline_id })
                        }}
                        className={`p-1.5 rounded-lg transition-colors ${chunk.is_flagged ? 'text-amber-500 bg-amber-50' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}
                        title={chunk.is_flagged ? 'Remove flag' : 'Flag for review'}
                      >
                        <Flag size={14} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Page {data.page} of {data.pages}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1.5 rounded-lg border border-border text-sm disabled:opacity-40 hover:bg-muted transition-colors">Prev</button>
            <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages}
              className="px-3 py-1.5 rounded-lg border border-border text-sm disabled:opacity-40 hover:bg-muted transition-colors">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
