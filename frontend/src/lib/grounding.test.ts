import { describe, expect, it } from 'vitest'
import { resolveSupportingChunk } from './grounding'

describe('resolveSupportingChunk', () => {
  const chunks = [
    { id: 'db-1', chunk_id: 'c-alpha', chunk_text: 'Alpha context' },
    { id: 'db-2', chunk_id: 'c-beta', chunk_text: 'Beta context' },
  ]

  it('matches by chunk_id', () => {
    const found = resolveSupportingChunk(
      { supporting_chunk_id: 'c-beta' },
      chunks,
    )
    expect(found?.chunk_text).toBe('Beta context')
  })

  it('matches by database id', () => {
    const found = resolveSupportingChunk(
      { supporting_chunk_id: 'db-1' },
      chunks,
    )
    expect(found?.chunk_id).toBe('c-alpha')
  })

  it('returns undefined when no supporting id', () => {
    expect(resolveSupportingChunk({}, chunks)).toBeUndefined()
    expect(
      resolveSupportingChunk({ supporting_chunk_id: null }, chunks),
    ).toBeUndefined()
  })

  it('returns undefined when chunk is missing', () => {
    expect(
      resolveSupportingChunk({ supporting_chunk_id: 'missing' }, chunks),
    ).toBeUndefined()
  })
})
