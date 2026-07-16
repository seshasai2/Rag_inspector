'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { GitBranch, Plus, Trash2, ArrowRightLeft, X } from 'lucide-react'

interface Pipeline { id: string; name: string; description?: string; created_at: string }
interface PipelineStats {
  pipeline_id: string; name: string; total_queries: number;
  hallucination_rate: number; mean_faithfulness: number;
  mean_context_precision: number; mean_latency_ms: number;
  failure_rate: number; queries_last_7d: number;
}

function StatDelta({ a, b, label, higherBetter = true }: { a: number; b: number; label: string; higherBetter?: boolean }) {
  const delta = b - a
  const isBetter = higherBetter ? delta > 0 : delta < 0
  const pctA = (a * 100).toFixed(1)
  const pctB = (b * 100).toFixed(1)

  return (
    <div className="flex items-center gap-2 py-2 border-b border-border last:border-0">
      <span className="text-sm text-muted-foreground flex-1">{label}</span>
      <span className="text-sm font-medium tabular-nums w-16 text-center">{pctA}%</span>
      <span className="text-xs text-muted-foreground">→</span>
      <span className="text-sm font-medium tabular-nums w-16 text-center">{pctB}%</span>
      {Math.abs(delta) > 0.001 && (
        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${isBetter ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
          {delta > 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
        </span>
      )}
    </div>
  )
}

export default function PipelinesPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [compareA, setCompareA] = useState('')
  const [compareB, setCompareB] = useState('')
  const [showCompare, setShowCompare] = useState(false)

  const queryClient = useQueryClient()

  const { data: pipelines, isLoading } = useQuery<Pipeline[]>({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then(r => r.data),
  })

  const { data: statsData } = useQuery({
    queryKey: ['pipeline-stats-all', pipelines],
    enabled: !!pipelines?.length,
    queryFn: async () => {
      const results = await Promise.allSettled(
        (pipelines || []).map(p => api.get(`/pipelines/${p.id}/stats`).then(r => r.data))
      )
      return results.map(r => r.status === 'fulfilled' ? r.value : null).filter(Boolean) as PipelineStats[]
    },
  })

  const { data: compareData, isLoading: compareLoading } = useQuery({
    queryKey: ['compare', compareA, compareB],
    enabled: !!(compareA && compareB && compareA !== compareB),
    queryFn: () => api.get('/pipelines/compare', { params: { a: compareA, b: compareB } }).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => api.post('/pipelines', { name: newName, description: newDesc }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      toast.success('Pipeline created')
    },
    onError: () => toast.error('Failed to create pipeline'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/pipelines/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      toast.success('Pipeline deleted')
    },
  })

  const statsMap = new Map(statsData?.map(s => [s.pipeline_id, s]))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Pipelines</h1>
          <p className="text-muted-foreground text-sm mt-1">Manage and compare your RAG pipelines</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCompare(!showCompare)}
            className="flex items-center gap-2 border border-border rounded-lg px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            <ArrowRightLeft size={15} />
            A/B Compare
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-primary text-primary-foreground rounded-lg px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus size={15} />
            New Pipeline
          </button>
        </div>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-foreground text-lg">New Pipeline</h2>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Pipeline name</label>
                <input value={newName} onChange={e => setNewName(e.target.value)}
                  placeholder="customer-support-rag"
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Description <span className="text-muted-foreground">(optional)</span></label>
                <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)}
                  placeholder="What does this pipeline do?"
                  rows={3}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="flex-1 border border-border rounded-lg py-2 text-sm font-medium hover:bg-muted transition-colors">Cancel</button>
                <button onClick={() => createMutation.mutate()} disabled={!newName || createMutation.isPending}
                  className="flex-1 bg-primary text-primary-foreground rounded-lg py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* A/B Compare panel */}
      {showCompare && (
        <div className="bg-card border border-border rounded-xl p-5 mb-6">
          <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
            <ArrowRightLeft size={16} />
            A/B Pipeline Comparison
          </h2>
          <div className="flex gap-3 mb-6 flex-wrap">
            <select value={compareA} onChange={e => setCompareA(e.target.value)}
              className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Select Pipeline A</option>
              {pipelines?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select value={compareB} onChange={e => setCompareB(e.target.value)}
              className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Select Pipeline B</option>
              {pipelines?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          {compareLoading && <div className="skeleton h-32 rounded-lg" />}

          {compareData && !compareLoading && (
            <div className="bg-muted/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-muted-foreground flex-1">Metric</span>
                <span className="text-xs font-semibold text-blue-600 w-16 text-center">{compareData.pipeline_a.name}</span>
                <span className="text-xs text-muted-foreground w-6 text-center">→</span>
                <span className="text-xs font-semibold text-purple-600 w-16 text-center">{compareData.pipeline_b.name}</span>
                <span className="text-xs text-muted-foreground w-16 text-center">Delta</span>
              </div>
              <StatDelta
                a={compareData.pipeline_a.mean_faithfulness}
                b={compareData.pipeline_b.mean_faithfulness}
                label="Mean Faithfulness"
                higherBetter
              />
              <StatDelta
                a={compareData.pipeline_a.mean_context_precision}
                b={compareData.pipeline_b.mean_context_precision}
                label="Context Precision"
                higherBetter
              />
              <StatDelta
                a={compareData.pipeline_a.hallucination_rate}
                b={compareData.pipeline_b.hallucination_rate}
                label="Hallucination Rate"
                higherBetter={false}
              />
              <StatDelta
                a={compareData.pipeline_a.mean_grounded_fraction}
                b={compareData.pipeline_b.mean_grounded_fraction}
                label="Grounding Rate"
                higherBetter
              />
              <StatDelta
                a={(compareData.pipeline_a.trust_score ?? 0) / 100}
                b={(compareData.pipeline_b.trust_score ?? 0) / 100}
                label="Trust Score"
                higherBetter
              />
              <div className="flex items-center gap-2 py-2 border-b border-border">
                <span className="text-sm text-muted-foreground flex-1">Hallucination Cost / mo</span>
                <span className="text-sm font-medium tabular-nums w-16 text-center">
                  ${(compareData.pipeline_a.hallucination_cost_usd ?? 0).toFixed(0)}
                </span>
                <span className="text-xs text-muted-foreground w-6 text-center">vs</span>
                <span className="text-sm font-medium tabular-nums w-16 text-center">
                  ${(compareData.pipeline_b.hallucination_cost_usd ?? 0).toFixed(0)}
                </span>
                <span className="w-16" />
              </div>
              <div className="flex items-center gap-2 py-2 mt-1">
                <span className="text-sm text-muted-foreground flex-1">Total Queries</span>
                <span className="text-sm font-medium tabular-nums w-16 text-center">{compareData.pipeline_a.total_queries}</span>
                <span className="text-xs text-muted-foreground w-6 text-center">vs</span>
                <span className="text-sm font-medium tabular-nums w-16 text-center">{compareData.pipeline_b.total_queries}</span>
                <span className="w-16" />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pipelines grid */}
      {isLoading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array(3).fill(0).map((_, i) => <div key={i} className="skeleton h-48 rounded-xl" />)}
        </div>
      ) : !pipelines?.length ? (
        <div className="text-center py-20">
          <GitBranch className="mx-auto mb-4 text-muted-foreground opacity-30" size={40} />
          <p className="text-foreground font-medium mb-2">No pipelines yet</p>
          <p className="text-muted-foreground text-sm mb-4">Create your first pipeline or send a trace via the SDK to auto-create one.</p>
          <button onClick={() => setShowCreate(true)} className="bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90">
            Create Pipeline
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pipelines.map(pipeline => {
            const stats = statsMap.get(pipeline.id)
            return (
              <div key={pipeline.id} className="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition-colors group">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                      <GitBranch size={15} className="text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground text-sm">{pipeline.name}</h3>
                      <p className="text-xs text-muted-foreground">{new Date(pipeline.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Delete pipeline "${pipeline.name}"? This cannot be undone.`)) {
                        deleteMutation.mutate(pipeline.id)
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all p-1"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {pipeline.description && (
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{pipeline.description}</p>
                )}

                {stats ? (
                  <div className="grid grid-cols-2 gap-2 mt-3">
                    {[
                      { label: 'Queries', value: stats.total_queries.toLocaleString() },
                      { label: 'Hallucination', value: `${(stats.hallucination_rate * 100).toFixed(1)}%` },
                      { label: 'Faithfulness', value: `${(stats.mean_faithfulness * 100).toFixed(1)}%` },
                      { label: 'Avg Latency', value: `${stats.mean_latency_ms.toFixed(0)}ms` },
                    ].map(s => (
                      <div key={s.label} className="bg-muted/40 rounded-lg p-2.5">
                        <p className="text-xs text-muted-foreground">{s.label}</p>
                        <p className="text-sm font-semibold text-foreground mt-0.5">{s.value}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2 mt-3">
                    {Array(4).fill(0).map((_, i) => <div key={i} className="skeleton h-14 rounded-lg" />)}
                  </div>
                )}

                <Link
                  href={`/queries?pipeline_id=${pipeline.id}`}
                  className="mt-4 block text-center text-xs text-primary hover:underline font-medium"
                >
                  View queries →
                </Link>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
