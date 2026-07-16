'use client'

import { cn } from '@/lib/utils'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

export type StageStatus = 'pending' | 'running' | 'ok' | 'warn' | 'error' | 'skipped'

export interface PipelineStageNode {
  id: string
  label: string
  latencyMs?: number | null
  status: StageStatus
  detail?: string
}

const STATUS_ICON = {
  pending: Circle,
  running: Loader2,
  ok: CheckCircle2,
  warn: CheckCircle2,
  error: XCircle,
  skipped: Circle,
} as const

const STATUS_CLASS: Record<StageStatus, string> = {
  pending: 'border-border text-muted-foreground',
  running: 'border-accent-blue/40 text-accent-blue',
  ok: 'border-accent-green/40 text-accent-green',
  warn: 'border-accent-amber/40 text-accent-amber',
  error: 'border-accent-red/40 text-accent-red',
  skipped: 'border-border text-muted-foreground/60',
}

/** Compact Embed → Retrieve → Rank → Generate → Ground → Evaluate pipeline timeline. */
export function PipelineStageGraph({
  stages,
  className,
}: {
  stages: PipelineStageNode[]
  className?: string
}) {
  return (
    <ol
      className={cn('grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6', className)}
      aria-label="Pipeline execution stages"
    >
      {stages.map((stage, index) => {
        const Icon = STATUS_ICON[stage.status]
        return (
          <li
            key={stage.id}
            className={cn(
              'rounded-xl border bg-card/60 p-3',
              STATUS_CLASS[stage.status],
            )}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon
                size={14}
                className={cn(stage.status === 'running' && 'animate-spin')}
                aria-hidden
              />
              <span className="text-xs font-medium text-foreground">
                {index + 1}. {stage.label}
              </span>
            </div>
            <p className="text-sm font-semibold text-foreground">
              {stage.latencyMs != null ? `${Math.round(stage.latencyMs)} ms` : '—'}
            </p>
            {stage.detail && (
              <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">{stage.detail}</p>
            )}
          </li>
        )
      })}
    </ol>
  )
}

export function buildTracePipelineStages(trace: {
  analysis_status: string
  embed_latency_ms?: number | null
  retrieve_latency_ms?: number | null
  rank_latency_ms?: number | null
  generate_latency_ms?: number | null
  grounded_fraction?: number | null
  faithfulness_score?: number | null
  is_hallucination?: boolean | null
  failure_type?: string | null
}): PipelineStageNode[] {
  const analyzing =
    trace.analysis_status === 'pending' || trace.analysis_status === 'analyzing'
  const failed = trace.analysis_status === 'failed'
  const done = trace.analysis_status === 'completed'

  const stage = (
    id: string,
    label: string,
    latencyMs: number | null | undefined,
    status: StageStatus,
    detail?: string,
  ): PipelineStageNode => ({ id, label, latencyMs, status, detail })

  return [
    stage(
      'embed',
      'Embedding',
      trace.embed_latency_ms,
      analyzing && trace.embed_latency_ms == null ? 'running' : trace.embed_latency_ms != null ? 'ok' : 'skipped',
    ),
    stage(
      'retrieve',
      'Retrieval',
      trace.retrieve_latency_ms,
      analyzing && trace.retrieve_latency_ms == null ? 'running' : trace.retrieve_latency_ms != null ? 'ok' : 'skipped',
    ),
    stage(
      'rank',
      'Rerank',
      trace.rank_latency_ms,
      trace.rank_latency_ms != null ? 'ok' : analyzing ? 'pending' : 'skipped',
      'Client-reported rank latency',
    ),
    stage(
      'generate',
      'Generation',
      trace.generate_latency_ms,
      analyzing && trace.generate_latency_ms == null ? 'running' : trace.generate_latency_ms != null ? 'ok' : 'skipped',
    ),
    stage(
      'ground',
      'Grounding',
      null,
      failed
        ? 'error'
        : analyzing
          ? 'running'
          : done
            ? trace.is_hallucination
              ? 'warn'
              : 'ok'
            : 'pending',
      done && trace.grounded_fraction != null
        ? `${(trace.grounded_fraction * 100).toFixed(0)}% grounded`
        : undefined,
    ),
    stage(
      'evaluate',
      'Evaluation',
      null,
      failed
        ? 'error'
        : analyzing
          ? 'running'
          : done
            ? 'ok'
            : 'pending',
      done && trace.faithfulness_score != null
        ? `Faithfulness ${(trace.faithfulness_score * 100).toFixed(0)}%`
        : trace.failure_type && trace.failure_type !== 'none'
          ? trace.failure_type.replace(/_/g, ' ')
          : undefined,
    ),
  ]
}
