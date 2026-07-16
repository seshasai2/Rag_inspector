'use client'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/lib/api'
import { ChartCard } from '@/components/ui/chart-card'
import { PageHeader } from '@/components/ui/page-header'
import { ErrorState } from '@/components/app-shell'
import { usePipelineId, usePipelines } from '@/hooks/usePipelineId'
import { getApiErrorMessage } from '@/lib/errors'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend
} from 'recharts'

const FAILURE_COLORS: Record<string, string> = {
  hallucination: '#ef4444',
  retrieval_miss: '#f59e0b',
  retrieval_irrelevant: '#f97316',
  coverage_gap: '#8b5cf6',
  chunking_issue: '#06b6d4',
  none: '#22c55e',
}

export default function MetricsPage() {
  const [days, setDays] = useState(30)
  const { pipelineId, setPipelineId } = usePipelineId()
  const { data: pipelines } = usePipelines()

  const params = { days, pipeline_id: pipelineId || undefined }

  const { data: faithTs, isLoading: l1, isError: e1, error: err1, refetch: r1 } = useQuery({
    queryKey: ['ts-faith', days, pipelineId],
    queryFn: () => api.get('/metrics/timeseries', { params: { ...params, metric: 'faithfulness_score' } }).then(r => r.data),
  })
  const { data: precTs, isLoading: l2 } = useQuery({
    queryKey: ['ts-prec', days, pipelineId],
    queryFn: () => api.get('/metrics/timeseries', { params: { ...params, metric: 'context_precision_score' } }).then(r => r.data),
  })
  const { data: groundTs, isLoading: l3 } = useQuery({
    queryKey: ['ts-ground', days, pipelineId],
    queryFn: () => api.get('/metrics/timeseries', { params: { ...params, metric: 'grounded_fraction' } }).then(r => r.data),
  })
  const { data: failDist, isLoading: l4 } = useQuery({
    queryKey: ['fail-dist-m', pipelineId],
    queryFn: () => api.get('/metrics/failure-distribution', { params: { pipeline_id: pipelineId || undefined } }).then(r => r.data),
  })
  const { data: latency, isLoading: l5 } = useQuery({
    queryKey: ['latency', days, pipelineId],
    queryFn: () => api.get('/metrics/latency-breakdown', { params }).then(r => r.data),
  })
  const { data: bm25Agg, isLoading: l6 } = useQuery({
    queryKey: ['bm25-agg', pipelineId],
    queryFn: () => api.get('/metrics/bm25-comparison', { params: { pipeline_id: pipelineId || undefined } }).then(r => r.data),
  })

  const tooltipStyle = {
    contentStyle: {
      background: 'hsl(var(--card))',
      border: '1px solid hsl(var(--border))',
      borderRadius: '8px',
      fontSize: 12,
    },
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Metrics"
        description="Aggregate RAGAS metrics and failure analysis"
        actions={
        <div className="flex gap-3">
          <select
            value={pipelineId || ''}
            onChange={e => setPipelineId(e.target.value || undefined)}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label="Filter by pipeline"
          >
            <option value="">All pipelines</option>
            {pipelines?.map((p: { id: string; name: string }) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        }
      />

      {e1 && (
        <ErrorState
          message={getApiErrorMessage(err1, 'Failed to load metrics timeseries.')}
          onRetry={() => r1()}
          title="Metrics unavailable"
        />
      )}

      <div className="mb-6">
        <ChartCard title="BM25 vs Vector (aggregate)" loading={l6}>
          {!bm25Agg || bm25Agg.traces_compared === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No comparable traces yet. Analyze queries to compute BM25 scores alongside vector similarity.
            </p>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-6 py-2">
              <div className="text-center">
                <p className="text-4xl font-bold text-accent-purple">
                  {((bm25Agg.bm25_outperform_rate ?? 0) * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">BM25 outperforms vector</p>
              </div>
              <div className="flex-1 space-y-2">
                <p className="text-sm text-foreground leading-relaxed">{bm25Agg.summary}</p>
                <p className="text-xs text-muted-foreground">
                  {bm25Agg.bm25_better_count}/{bm25Agg.traces_compared} traces · margin +{(bm25Agg.margin ?? 0.15) * 100}%
                </p>
                {bm25Agg.recommend_hybrid && (
                  <p className="text-xs font-medium text-accent-purple bg-accent-purple/10 border border-accent-purple/30 rounded-lg px-3 py-2">
                    Recommendation: consider hybrid retrieval (BM25 + vector)
                  </p>
                )}
              </div>
            </div>
          )}
        </ChartCard>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Faithfulness over time */}
        <ChartCard title="Faithfulness Score" loading={l1}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={faithTs?.data ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} stroke="hsl(var(--muted-foreground))" />
              <Tooltip {...tooltipStyle} formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Faithfulness']} />
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Context precision over time */}
        <ChartCard title="Context Precision" loading={l2}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={precTs?.data ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} stroke="hsl(var(--muted-foreground))" />
              <Tooltip {...tooltipStyle} formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Context Precision']} />
              <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Grounded fraction over time */}
        <ChartCard title="Grounding Rate" loading={l3}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={groundTs?.data ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} stroke="hsl(var(--muted-foreground))" />
              <Tooltip {...tooltipStyle} formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Grounded']} />
              <Line type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Failure distribution pie */}
        <ChartCard title="Failure Type Distribution" loading={l4}>
          {!failDist?.data?.length ? (
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">No failures recorded</div>
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="60%" height={200}>
                <PieChart>
                  <Pie data={failDist.data} dataKey="count" nameKey="failure_type" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                    {failDist.data.map((entry: { failure_type: string }, i: number) => (
                      <Cell key={i} fill={FAILURE_COLORS[entry.failure_type] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {failDist.data.map((d: { failure_type: string; count: number }) => (
                  <div key={d.failure_type} className="flex items-center gap-2 text-xs">
                    <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: FAILURE_COLORS[d.failure_type] || '#94a3b8' }} />
                    <span className="text-muted-foreground capitalize flex-1">{d.failure_type.replace(/_/g, ' ')}</span>
                    <span className="font-semibold text-foreground tabular-nums">{d.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ChartCard>

        {/* Latency breakdown */}
        <div className="lg:col-span-2">
          <ChartCard title="Latency Breakdown (ms)" loading={l5}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={latency?.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip {...tooltipStyle} formatter={(v: number, name: string) => [`${v.toFixed(0)}ms`, name]} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="embed_ms" name="Embed" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} />
                <Bar dataKey="retrieve_ms" name="Retrieve" stackId="a" fill="#8b5cf6" />
                <Bar dataKey="generate_ms" name="Generate" stackId="a" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </div>
    </div>
  )
}
