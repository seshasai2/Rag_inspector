'use client'

import type { ElementType, ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { surfaces } from '@/lib/design-tokens'

export type PanelProps = {
  children: ReactNode
  className?: string
  variant?: 'glass' | 'solid' | 'danger' | 'warning'
  title?: string
  icon?: ElementType
}

const variantClass: Record<NonNullable<PanelProps['variant']>, string> = {
  glass: surfaces.glass,
  solid: surfaces.solid,
  danger:
    'bg-gradient-to-br from-red-950/40 to-card/80 backdrop-blur-xl border border-accent-red/20 rounded-2xl relative overflow-hidden',
  warning:
    'bg-gradient-to-r from-accent-amber/10 to-orange-500/10 backdrop-blur-xl border border-accent-amber/20 rounded-2xl',
}

export function Panel({
  children,
  className,
  variant = 'glass',
  title,
  icon: Icon,
}: PanelProps) {
  return (
    <section className={cn(variantClass[variant], 'p-5 md:p-6', className)}>
      {(title || Icon) && (
        <div className="flex items-center gap-2 mb-4">
          {Icon && <Icon size={18} className="text-primary" />}
          {title && <h2 className="font-semibold text-foreground">{title}</h2>}
        </div>
      )}
      {children}
    </section>
  )
}
