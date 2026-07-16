import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TrustScoreGauge } from './trust-score-gauge'

describe('TrustScoreGauge', () => {
  it('renders the trust score hero metric', () => {
    render(<TrustScoreGauge score={87} />)
    expect(screen.getByTestId('trust-score-gauge')).toBeInTheDocument()
    expect(screen.getByText('Trust Score')).toBeInTheDocument()
    expect(screen.getByTestId('trust-score-value')).toHaveTextContent('87')
    expect(screen.getByText('/100')).toBeInTheDocument()
    expect(screen.getByTestId('trust-score-bar')).toHaveStyle({ width: '87%' })
  })

  it('shows low-trust guidance below 60', () => {
    render(<TrustScoreGauge score={42} />)
    expect(screen.getByText(/unreliable answers/i)).toBeInTheDocument()
  })

  it('shows high-trust guidance at 80+', () => {
    render(<TrustScoreGauge score={91} />)
    expect(screen.getByText(/highly trustworthy/i)).toBeInTheDocument()
  })
})
