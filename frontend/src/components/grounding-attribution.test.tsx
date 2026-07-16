import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GroundingAttributionPanel } from './grounding-attribution'

const chunks = [
  {
    id: 'db-1',
    chunk_id: 'chunk-a',
    chunk_text: 'Paris is the capital of France.',
    rank: 1,
    similarity_score: 0.92,
    was_cited: true,
  },
  {
    id: 'db-2',
    chunk_id: 'chunk-b',
    chunk_text: 'Unrelated weather notes.',
    rank: 2,
    was_cited: false,
  },
]

const sentences = [
  {
    sentence_text: 'The capital of France is Paris.',
    sentence_index: 0,
    is_grounded: true,
    supporting_chunk_id: 'chunk-a',
    confidence_score: 0.95,
  },
  {
    sentence_text: 'It has three moons.',
    sentence_index: 1,
    is_grounded: false,
  },
]

describe('GroundingAttributionPanel', () => {
  it('renders sentence grounding summary', () => {
    render(
      <GroundingAttributionPanel
        sentences={sentences}
        chunks={chunks}
        groundedFraction={0.5}
        isHallucination={true}
      />,
    )
    expect(screen.getByText('Sentence Grounding')).toBeInTheDocument()
    expect(screen.getByText('1/2 grounded · 50%')).toBeInTheDocument()
    expect(screen.getByText(/Hallucination detected/i)).toBeInTheDocument()
    expect(screen.getByText('The capital of France is Paris.')).toBeInTheDocument()
  })

  it('highlights supporting chunk on sentence hover', async () => {
    const user = userEvent.setup()
    render(
      <GroundingAttributionPanel sentences={sentences} chunks={chunks} />,
    )

    const chunkCard = screen.getByTestId('chunk-card-chunk-a')
    expect(chunkCard).toHaveAttribute('data-highlighted', 'false')

    await user.hover(screen.getByText('The capital of France is Paris.'))

    expect(chunkCard).toHaveAttribute('data-highlighted', 'true')
    expect(screen.getByText(/Supports hovered sentence/i)).toBeInTheDocument()
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Paris is the capital of France.',
    )
  })

  it('shows fallback when grounding results are empty', () => {
    render(
      <GroundingAttributionPanel
        sentences={[]}
        chunks={[]}
        fallbackAnswer="Raw answer text"
      />,
    )
    expect(screen.getByText('Raw answer text')).toBeInTheDocument()
    expect(
      screen.getByText(/Grounding results appear after analysis/i),
    ).toBeInTheDocument()
  })
})
