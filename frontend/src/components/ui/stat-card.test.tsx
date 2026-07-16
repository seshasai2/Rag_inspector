import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Activity } from 'lucide-react'
import { StatCard } from '@/components/ui/stat-card'
import { accentTones, surfaces } from '@/lib/design-tokens'

describe('design tokens', () => {
  it('exposes accent tones and surfaces', () => {
    expect(accentTones.blue.text).toContain('accent-blue')
    expect(surfaces.glass).toContain('bg-card')
  })
})

describe('StatCard', () => {
  it('renders label, value, and trend', () => {
    render(
      <StatCard
        label="Total Queries"
        value={42}
        icon={Activity}
        color="blue"
        trend={12}
      />,
    )
    expect(screen.getByText('Total Queries')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('+12%')).toBeInTheDocument()
  })
})
