'use client'

import { TrendingUp } from 'lucide-react'
import type { ElementType } from 'react'
import { accentTones, type AccentTone, surfaces } from '@/lib/design-tokens'
import { cn } from '@/lib/utils'

export type StatCardProps = {
  label: string
  value: string | number
  sub?: string
  color?: AccentTone
  icon?: ElementType
  /** Week-over-week relative % change. Omit / null when baseline is insufficient. */
  trend?: number | null
  /** When true, decreases are shown as positive (e.g. hallucination rate). */
  preferLower?: boolean
  className?: string
}

export function StatCard({
  label,
  value,
  sub,
  color = 'blue',
  icon: Icon,
  trend,
  preferLower = false,
  className,
}: StatCardProps) {
  const c = accentTones[color] ?? accentTones.blue
  const showTrend = trend !== undefined && trend !== null && !Number.isNaN(trend)
  const isImprovement = showTrend ? (preferLower ? trend! <= 0 : trend! >= 0) : false

  return (
    <div className={cn(surfaces.glass, 'p-6 group', className)}>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground font-medium">{label}</p>
        {Icon && (
          <div
            className={cn(
              'w-10 h-10 rounded-xl border flex items-center justify-center',
              c.bg,
              c.text,
              c.border,
            )}
          >
            <Icon size={18} />
          </div>
        )}
      </div>
      <div className="flex items-end gap-3">
        <p className="text-3xl font-bold text-foreground">{value}</p>
        {showTrend && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs font-medium',
              isImprovement ? 'text-accent-green' : 'text-accent-red',
            )}
            title="Week-over-week change vs prior 7 days"
          >
            <TrendingUp size={12} className={trend! < 0 ? 'rotate-180' : ''} />
            {trend! >= 0 ? '+' : ''}
            {trend}%
          </div>
        )}
      </div>
      {sub && <p className="text-xs text-muted-foreground/80 mt-2">{sub}</p>}
    </div>
  )
}
