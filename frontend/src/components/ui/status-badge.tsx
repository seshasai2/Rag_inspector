'use client'

import { cn } from '@/lib/utils'

const FAILURE_STYLES: Record<string, string> = {
  hallucination: 'bg-accent-red/15 text-accent-red border-accent-red/30',
  retrieval_miss: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  retrieval_irrelevant: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  coverage_gap: 'bg-accent-purple/15 text-accent-purple border-accent-purple/30',
  chunking_issue: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  none: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  success: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  pending: 'bg-muted text-muted-foreground border-border',
  analyzing: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  completed: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  failed: 'bg-accent-red/15 text-accent-red border-accent-red/30',
}

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string
  label?: string
  className?: string
}) {
  const key = (status || 'none').toLowerCase()
  const style = FAILURE_STYLES[key] || 'bg-muted text-muted-foreground border-border'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
        style,
        className,
      )}
    >
      {label ?? status.replace(/_/g, ' ')}
    </span>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={cn('skeleton rounded-xl', className)} aria-hidden />
}
