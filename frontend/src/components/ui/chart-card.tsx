'use client'

import type { ReactNode } from 'react'
import { Panel } from '@/components/ui/panel'

export function ChartCard({
  title,
  children,
  loading,
}: {
  title: string
  children: ReactNode
  loading?: boolean
}) {
  return (
    <Panel variant="solid" className="p-5">
      <h2 className="font-semibold text-foreground mb-4">{title}</h2>
      {loading ? <div className="skeleton h-48 rounded-lg" /> : children}
    </Panel>
  )
}
