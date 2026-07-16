'use client'
import api from '@/lib/api'
import { ErrorState } from '@/components/app-shell'
import { TrustScoreGauge } from '@/components/trust-score-gauge'
import { Panel } from '@/components/ui/panel'
import { StatCard } from '@/components/ui/stat-card'
import { usePipelineId } from '@/hooks/usePipelineId'
import { getApiErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle, Lightbulb, ArrowUpRight } from 'lucide-react'
import Link from 'next/link'
import { Suspense, useEffect, useState } from 'react'
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis, YAxis, Area, AreaChart
} from 'recharts'

function HallucinationCostCard({
  costUsd,
  rate,
  queriesPerMonth,
  costPerWrong,
  pipelineId,
  onSaved,
}: {
  costUsd: number
  rate: number
  queriesPerMonth: number
  costPerWrong: number
  pipelineId?: string | null
  onSaved?: () => void
}) {
  const [queries, setQueries] = useState(queriesPerMonth)
  const [unitCost, setUnitCost] = useState(costPerWrong)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const editable = Boolean(pipelineId)

  useEffect(() => {
    setQueries(queriesPerMonth)
    setUnitCost(costPerWrong)
  }, [queriesPerMonth, costPerWrong, pipelineId])

  const previewCost = editable
    ? Math.round(queries * rate * unitCost * 100) / 100
    : costUsd

  async function save() {
    if (!pipelineId) return
    setSaving(true)
    setError(null)
    try {
      await api.patch(`/pipelines/${pipelineId}`, {
        queries_per_month: Math.max(0, Math.round(queries)),
        cost_per_wrong_answer_usd: Math.max(0, unitCost),
      })
      onSaved?.()
    } catch {
      setError('Could not save cost settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel variant="danger" className="p-6">
      <div className="absolute top-0 right-0 w-28 h-28 bg-accent-red/10 rounded-full blur-3xl" />
      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm text-muted-foreground font-medium">Hallucination Cost</p>
          <div className="w-10 h-10 rounded-xl bg-red-500/10 text-accent-red border border-red-500/20 flex items-center justify-center">
            <AlertTriangle size={18} />
          </div>
        </div>
        <p className="text-4xl font-bold text-accent-red mb-1">
          ${previewCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          <span className="text-lg text-muted-foreground/80 font-medium">/mo</span>
        </p>
        <p className="text-xs text-muted-foreground/80 mb-4 leading-relaxed">
          {(rate * 100).toFixed(1)}% rate × {queries.toLocaleString()} queries/mo × ${Number(unitCost).toFixed(2)}/wrong answer
        </p>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted-foreground/80 space-y-1">
            Queries / month
            <input
              type="number"
              min={0}
              disabled={!editable}
              value={queries}
              onChange={(e) => setQueries(Number(e.target.value) || 0)}
              className="w-full bg-muted/80 border border-border rounded-lg px-3 py-2 text-sm text-foreground disabled:opacity-50"
            />
          </label>
          <label className="text-xs text-muted-foreground/80 space-y-1">
            Cost / wrong answer ($)
            <input
              type="number"
              min={0}
              step={0.5}
              disabled={!editable}
              value={unitCost}
              onChange={(e) => setUnitCost(Number(e.target.value) || 0)}
              className="w-full bg-muted/80 border border-border rounded-lg px-3 py-2 text-sm text-foreground disabled:opacity-50"
            />
          </label>
        </div>
        {editable ? (
          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="mt-3 w-full px-3 py-2 rounded-xl text-sm font-medium bg-accent-red/20 text-accent-red border border-accent-red/30 hover:bg-accent-red/30 disabled:opacity-50 transition-all"
          >
            {saving ? 'Saving…' : 'Save cost assumptions'}
          </button>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground/80">Select a pipeline to edit cost assumptions.</p>
        )}
        {error && <p className="mt-2 text-xs text-accent-red">{error}</p>}
      </div>
    </Panel>
  )
}

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`bg-muted/50 rounded-2xl animate-pulse ${className}`} />
}

const FAILURE_COLORS: Record<string, string> = {
  hallucination: '#ef4444',
  retrieval_miss: '#f59e0b',
  retrieval_irrelevant: '#f97316',
  coverage_gap: '#8b5cf6',
  chunking_issue: '#06b6d4',
  none: '#22c55e',
}

function DashboardContent() {
  const { user } = useAuthStore()
  const { pipelineId, withPipeline } = usePipelineId()

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard', pipelineId],
    queryFn: () => api.get('/metrics/dashboard', { params: { pipeline_id: pipelineId } }).then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: timeseries, isError: tsError, refetch: refetchTs } = useQuery({
    queryKey: ['timeseries-faith', pipelineId],
    queryFn: () => api.get('/metrics/timeseries', { params: { metric: 'faithfulness_score', days: 14, pipeline_id: pipelineId } }).then(r => r.data),
  })

  const { data: failDist, isError: failError, refetch: refetchFail } = useQuery({
    queryKey: ['fail-dist', pipelineId],
    queryFn: () => api.get('/metrics/failure-distribution', { params: { pipeline_id: pipelineId } }).then(r => r.data),
  })

  const hallucinationPct = data ? (data.hallucination_rate * 100).toFixed(1) : '—'
  const trustScore = data?.trustworthiness_score ?? 0

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
            <p className="text-muted-foreground">
              Welcome back, <span className="text-foreground font-medium">{user?.name}</span>. Here is your RAG pipeline health overview.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href={withPipeline('/metrics')}
              className="px-4 py-2 bg-muted/50 border border-border rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
            >
              View metrics
            </Link>
            <Link
              href={withPipeline('/queries')}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-xl text-sm text-foreground font-medium transition-all"
            >
              Browse queries
            </Link>
          </div>
        </div>
      </div>

      {isError && (
        <ErrorState
          message={getApiErrorMessage(error, 'Failed to load dashboard metrics.')}
          onRetry={() => refetch()}
          title="Dashboard unavailable"
        />
      )}
      {(tsError || failError) && !isError && (
        <div className="mb-6 rounded-xl border border-accent-amber/30 bg-accent-amber/10 px-4 py-3 text-sm text-accent-amber flex items-center justify-between gap-4">
          <span>Some charts failed to load.</span>
          <button
            type="button"
            onClick={() => { refetchTs(); refetchFail() }}
            className="px-3 py-1.5 rounded-lg bg-accent-amber/20 border border-accent-amber/30 hover:bg-accent-amber/30 text-foreground"
          >
            Retry charts
          </button>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {isLoading ? (
          Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-36" />)
        ) : (
          <>
            <div className="lg:col-span-1">
              <TrustScoreGauge score={trustScore} />
            </div>
            <HallucinationCostCard
              costUsd={data?.hallucination_cost_usd ?? 0}
              rate={data?.hallucination_rate ?? 0}
              queriesPerMonth={data?.queries_per_month ?? 10000}
              costPerWrong={data?.cost_per_wrong_answer_usd ?? 5}
              pipelineId={data?.cost_pipeline_id ?? pipelineId}
              onSaved={() => refetch()}
            />
            <StatCard 
              label="Total Queries" 
              value={data?.total_queries?.toLocaleString() ?? 0} 
              sub={`${data?.queries_today ?? 0} today`} 
              icon={Activity} 
              color="blue"
              trend={data?.queries_trend_pct ?? null}
            />
            <StatCard 
              label="Hallucination Rate" 
              value={`${hallucinationPct}%`} 
              sub="Lower is better · WoW vs prior week" 
              icon={AlertTriangle} 
              color={parseFloat(hallucinationPct) > 20 ? 'red' : 'green'}
              trend={data?.hallucination_rate_trend_pct ?? null}
              preferLower
            />
          </>
        )}
      </div>

      {/* BM25 aggregate (PRD F4) */}
      {data?.bm25_traces_compared > 0 && (
        <div className="mb-8 bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium mb-1">BM25 vs Vector</p>
              <p className="text-3xl font-bold text-accent-purple">
                {((data.bm25_outperform_rate ?? 0) * 100).toFixed(0)}%
                <span className="text-sm font-medium text-muted-foreground/80 ml-2">BM25 wins</span>
              </p>
            </div>
            <p className="text-sm text-muted-foreground flex-1 leading-relaxed">
              {data.bm25_summary}
            </p>
            <Link
              href={withPipeline('/metrics')}
              className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1 shrink-0"
            >
              View metrics <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>
      )}

      {/* Charts Section */}
      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        {/* Faithfulness over time */}
        <div className="lg:col-span-2 bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Faithfulness Score</h2>
              <p className="text-sm text-muted-foreground">Last 14 days trend</p>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-lg">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400 font-medium">Live</span>
            </div>
          </div>
          {!timeseries ? <Skeleton className="h-64" /> : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={timeseries.data}>
                <defs>
                  <linearGradient id="colorFaith" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="rgba(148, 163, 184, 0.3)" />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="rgba(148, 163, 184, 0.3)" />
                <Tooltip
                  contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '12px', fontSize: 12, color: '#fff' }}
                  formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Faithfulness']}
                />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorFaith)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Failure distribution */}
        <div className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-foreground">Failure Distribution</h2>
            <p className="text-sm text-muted-foreground">By failure type</p>
          </div>
          {!failDist ? <Skeleton className="h-64" /> : failDist.data.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
              <CheckCircle className="mb-3 text-green-400" size={32} />
              <p className="text-sm">No failures detected 🎉</p>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={failDist.data} dataKey="count" nameKey="failure_type" cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={2}>
                    {failDist.data.map((entry: { failure_type: string }, i: number) => (
                      <Cell key={i} fill={FAILURE_COLORS[entry.failure_type] || '#94a3b8'} stroke="rgba(15, 23, 42, 0.5)" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number, n: string) => [v, n]} contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '12px', fontSize: 12, color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-4">
                {failDist.data.map((d: { failure_type: string; count: number }) => (
                  <Link
                    key={d.failure_type}
                    href={withPipeline(`/queries?failure_type=${encodeURIComponent(d.failure_type)}`)}
                    className="flex items-center gap-3 text-sm hover:bg-muted/50 rounded-lg px-2 py-1.5 -mx-2 transition-colors"
                  >
                    <div className="w-3 h-3 rounded-full" style={{ background: FAILURE_COLORS[d.failure_type] || '#94a3b8' }} />
                    <span className="text-muted-foreground capitalize flex-1">{d.failure_type.replace('_', ' ')}</span>
                    <span className="font-medium text-foreground">{d.count}</span>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Fix Recommendations */}
      {data?.recent_recommendations?.length > 0 && (
        <div className="bg-gradient-to-r from-accent-amber/10 to-orange-500/10 backdrop-blur-xl border border-accent-amber/20 rounded-2xl p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
                <Lightbulb size={18} className="text-amber-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Automated Fix Recommendations</h2>
                <p className="text-sm text-muted-foreground">AI-suggested improvements</p>
              </div>
            </div>
            <Link
              href={withPipeline('/autofix')}
              className="text-sm text-amber-400 hover:text-amber-300 font-medium flex items-center gap-1"
            >
              View all <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="space-y-3">
            {data.recent_recommendations.map((rec: { id: string; recommendation_type: string; topic_description: string; affected_query_count: number }) => (
              <div key={rec.id} className="flex items-start gap-4 p-4 bg-slate-900/50 border border-slate-800/50 rounded-xl hover:border-border transition-all group cursor-pointer">
                <div className="w-2 h-2 mt-2 rounded-full bg-amber-400 shrink-0 group-hover:scale-125 transition-transform" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground font-medium">{rec.topic_description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {rec.affected_query_count} queries affected · Type: <span className="text-amber-400 capitalize">{rec.recommendation_type.replace('_', ' ')}</span>
                  </p>
                </div>
                <ArrowUpRight size={16} className="text-muted-foreground/80 group-hover:text-amber-400 transition-colors" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent failures */}
      <div className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Recent Hallucinations</h2>
            <p className="text-sm text-muted-foreground">Queries requiring attention</p>
          </div>
          <Link href={withPipeline('/queries?is_hallucination=true')} className="text-sm text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1">
            View all <ArrowUpRight size={14} />
          </Link>
        </div>
        {isLoading ? (
          <div className="space-y-3">{Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
        ) : !data?.recent_failures?.length ? (
          <div className="text-center py-16 text-muted-foreground">
            <div className="w-16 h-16 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="text-green-400" size={32} />
            </div>
            <p className="text-sm font-medium text-foreground mb-1">All systems healthy</p>
            <p className="text-xs">No hallucinations detected in your pipeline</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {data.recent_failures.map((trace: { id: string; query_text: string; pipeline_name?: string; faithfulness_score?: number; failure_type?: string; traced_at: string }) => (
              <Link key={trace.id} href={`/queries/${trace.id}`} className="flex items-center gap-4 py-4 hover:bg-muted/30 rounded-xl px-4 -mx-4 transition-all group">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate group-hover:text-blue-400 transition-colors">{trace.query_text}</p>
                  <p className="text-xs text-muted-foreground mt-1">{trace.pipeline_name} · {new Date(trace.traced_at).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {trace.failure_type && trace.failure_type !== 'none' && (
                    <span className="text-xs bg-red-500/10 text-accent-red border border-red-500/20 px-3 py-1 rounded-lg font-medium capitalize">
                      {trace.failure_type.replace('_', ' ')}
                    </span>
                  )}
                  {trace.faithfulness_score != null && (
                    <span className={`text-xs font-bold tabular-nums px-3 py-1 rounded-lg ${
                      trace.faithfulness_score < 0.5 ? 'bg-red-500/10 text-accent-red border border-red-500/20' : 
                      trace.faithfulness_score < 0.7 ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 
                      'bg-green-500/10 text-green-400 border border-green-500/20'
                    }`}>
                      {(trace.faithfulness_score * 100).toFixed(0)}%
                    </span>
                  )}
                  <ArrowUpRight size={16} className="text-muted-foreground/80 group-hover:text-blue-400 transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8"><Skeleton className="h-96" /></div>}>
      <DashboardContent />
    </Suspense>
  )
}
