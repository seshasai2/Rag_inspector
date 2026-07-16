'use client'
import api from '@/lib/api'
import { GroundingAttributionPanel } from '@/components/grounding-attribution'
import { BM25ComparisonCard } from '@/components/bm25-comparison'
import {
  PipelineStageGraph,
  buildTracePipelineStages,
} from '@/components/pipeline-stage-graph'
import { ErrorState } from '@/components/app-shell'
import { StatusBadge } from '@/components/ui/status-badge'
import { getApiErrorMessage } from '@/lib/errors'
import { usePipelineId } from '@/hooks/usePipelineId'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, ChevronLeft, Clock, Info } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

interface Chunk {
  id: string
  chunk_id: string
  chunk_text: string
  similarity_score?: number
  bm25_score?: number
  rank?: number
  was_cited: boolean
  metadata?: Record<string, unknown>
}
interface GroundingResult {
  sentence_text: string
  sentence_index: number
  is_grounded: boolean
  supporting_chunk_id?: string
  confidence_score?: number
}
interface TraceDetail {
  id: string
  query_text: string
  answer_text?: string
  raw_context?: string
  pipeline_name?: string
  pipeline_id: string
  faithfulness_score?: number
  answer_relevance_score?: number
  context_precision_score?: number
  context_recall_score?: number
  grounded_fraction?: number
  is_hallucination?: boolean
  failure_type?: string
  failure_explanation?: string
  recommendation?: string
  embed_latency_ms?: number
  retrieve_latency_ms?: number
  rank_latency_ms?: number
  generate_latency_ms?: number
  analysis_status: string
  traced_at: string
  session_id?: string
  request_id?: string
  retrieved_chunks: Chunk[]
  grounding_results: GroundingResult[]
  bm25_comparison?: {
    bm25_better: boolean
    top_vector_score?: number | null
    top_bm25_score?: number | null
    comparable?: boolean
    analysis: string
  }
}

function MetricBar({ label, value }: { label: string; value?: number | null }) {
  const pct = value != null ? value * 100 : null
  const barColor =
    value == null
      ? 'bg-muted'
      : value >= 0.7
        ? 'bg-accent-green'
        : value >= 0.5
          ? 'bg-accent-amber'
          : 'bg-accent-red'
  const textColor =
    pct == null
      ? 'text-muted-foreground'
      : pct >= 70
        ? 'text-accent-green'
        : pct >= 50
          ? 'text-accent-amber'
          : 'text-accent-red'

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className={`text-sm font-semibold ${textColor}`}>
          {pct == null ? '—' : `${pct.toFixed(1)}%`}
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct ?? 0}%` }} />
      </div>
    </div>
  )
}

function LatencyStep({ label, ms, total }: { label: string; ms?: number | null; total: number }) {
  const pct = ms && total > 0 ? (ms / total) * 100 : 0
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-xs text-muted-foreground text-right">{label}</div>
      <div className="flex-1 h-6 bg-muted rounded-lg overflow-hidden relative">
        <div className="h-full bg-primary/20 rounded-lg" style={{ width: `${Math.max(pct, 2)}%` }} />
        <span className="absolute inset-0 flex items-center px-2 text-xs font-medium text-foreground">
          {ms != null ? `${ms.toFixed(0)}ms` : '—'}
        </span>
      </div>
    </div>
  )
}

export default function QueryDetailPage() {
  const { id } = useParams() as { id: string }
  const { withPipeline } = usePipelineId()

  const {
    data: trace,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<TraceDetail>({
    queryKey: ['trace', id],
    queryFn: () => api.get(`/queries/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || data.analysis_status === 'pending' || data.analysis_status === 'analyzing') {
        return 3000
      }
      return false
    },
  })

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="skeleton h-8 w-64 rounded" />
          <div className="skeleton h-40 rounded-xl" />
          <div className="skeleton h-80 rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        message={getApiErrorMessage(error, 'Failed to load this query.')}
        onRetry={() => refetch()}
        title="Query unavailable"
      />
    )
  }

  if (!trace) {
    return (
      <ErrorState
        message="This trace was not found or you do not have access."
        title="Trace not found"
      />
    )
  }

  const totalLatency =
    (trace.embed_latency_ms ?? 0) +
    (trace.retrieve_latency_ms ?? 0) +
    (trace.rank_latency_ms ?? 0) +
    (trace.generate_latency_ms ?? 0)
  const stages = buildTracePipelineStages(trace)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link
          href={withPipeline('/queries')}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Back to queries"
        >
          <ChevronLeft size={20} />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold text-foreground line-clamp-1">{trace.query_text}</h1>
          <p className="text-sm text-muted-foreground">
            {trace.pipeline_name} · {new Date(trace.traced_at).toLocaleString()}
            {trace.request_id ? ` · req ${trace.request_id.slice(0, 8)}` : ''}
          </p>
        </div>
        <StatusBadge status={trace.analysis_status} />
      </div>

      <div className="mb-6 bg-card border border-border rounded-xl p-5">
        <h2 className="font-semibold text-foreground mb-3 flex items-center gap-2">
          <Clock size={16} className="text-muted-foreground" /> Pipeline execution
        </h2>
        <PipelineStageGraph stages={stages} />
      </div>

      {(trace.answer_text || trace.grounding_results.length > 0) && (
        <div className="mb-6">
          <GroundingAttributionPanel
            sentences={trace.grounding_results}
            chunks={trace.retrieved_chunks}
            groundedFraction={trace.grounded_fraction}
            isHallucination={trace.is_hallucination}
            fallbackAnswer={trace.answer_text}
          />
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-xl p-5">
            <h2 className="font-semibold text-foreground mb-3">Query</h2>
            <p className="text-foreground bg-muted/50 rounded-lg p-3 text-sm">{trace.query_text}</p>
          </div>

          <div className="bg-card border border-border rounded-xl p-5">
            <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <Clock size={16} className="text-muted-foreground" /> Latency breakdown
            </h2>
            <div className="space-y-3">
              <LatencyStep label="Embed" ms={trace.embed_latency_ms} total={totalLatency} />
              <LatencyStep label="Retrieve" ms={trace.retrieve_latency_ms} total={totalLatency} />
              <LatencyStep label="Rerank" ms={trace.rank_latency_ms} total={totalLatency} />
              <LatencyStep label="Generate" ms={trace.generate_latency_ms} total={totalLatency} />
            </div>
            <p className="text-xs text-muted-foreground mt-3 text-right">
              Total: {totalLatency.toFixed(0)}ms
            </p>
          </div>

          <BM25ComparisonCard comparison={trace.bm25_comparison} chunks={trace.retrieved_chunks} />

          {trace.retrieved_chunks.some((c) => c.metadata && Object.keys(c.metadata).length > 0) && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold text-foreground mb-3">Chunk metadata</h2>
              <div className="space-y-2">
                {trace.retrieved_chunks.map((chunk) =>
                  chunk.metadata && Object.keys(chunk.metadata).length > 0 ? (
                    <div key={chunk.id} className="text-xs text-muted-foreground flex flex-wrap gap-1">
                      <span className="font-mono mr-2">{chunk.chunk_id.slice(0, 12)}…</span>
                      {Object.entries(chunk.metadata)
                        .slice(0, 4)
                        .map(([k, v]) => (
                          <span key={k} className="bg-muted px-2 py-0.5 rounded">
                            {k}: {String(v).slice(0, 40)}
                          </span>
                        ))}
                    </div>
                  ) : null,
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-5">
            <h2 className="font-semibold text-foreground mb-4">RAGAS metrics</h2>
            <div className="space-y-4">
              <MetricBar label="Faithfulness" value={trace.faithfulness_score} />
              <MetricBar label="Answer Relevance" value={trace.answer_relevance_score} />
              <MetricBar label="Context Precision" value={trace.context_precision_score} />
              <MetricBar label="Context Recall" value={trace.context_recall_score} />
              <MetricBar label="Grounded Fraction" value={trace.grounded_fraction} />
            </div>
            {trace.analysis_status !== 'completed' && (
              <p className="text-xs text-muted-foreground mt-4 animate-pulse">Analysis in progress…</p>
            )}
          </div>

          {trace.failure_type && trace.failure_type !== 'none' && (
            <div className="border border-accent-amber/30 bg-accent-amber/10 rounded-xl p-5 text-accent-amber">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={16} />
                <h2 className="font-semibold capitalize text-foreground">
                  {trace.failure_type.replace(/_/g, ' ')}
                </h2>
                <StatusBadge status={trace.failure_type} />
              </div>
              <p className="text-sm leading-relaxed mb-3 text-foreground/90">
                {trace.failure_explanation}
              </p>
            </div>
          )}

          {trace.failure_type === 'none' && trace.analysis_status === 'completed' && (
            <div className="bg-accent-green/10 border border-accent-green/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2 text-accent-green">
                <CheckCircle size={16} />
                <h2 className="font-semibold">No issues detected</h2>
              </div>
              <p className="text-sm text-foreground/80">This query processed successfully.</p>
            </div>
          )}

          {trace.recommendation && trace.failure_type !== 'none' && (
            <div className="bg-accent-blue/10 border border-accent-blue/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2 text-accent-blue">
                <Info size={16} />
                <h2 className="font-semibold">Recommendation</h2>
              </div>
              <p className="text-sm text-foreground/90 leading-relaxed">{trace.recommendation}</p>
            </div>
          )}

          {trace.raw_context && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold text-foreground mb-3">Context sent to LLM</h2>
              <div className="max-h-48 overflow-y-auto">
                <p className="text-xs text-muted-foreground font-mono leading-relaxed whitespace-pre-wrap">
                  {trace.raw_context}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
