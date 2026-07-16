/** Shared grounding attribution helpers (query detail key page). */

export interface GroundingChunkRef {
  id: string
  chunk_id: string
  chunk_text: string
}

export interface GroundingSentenceRef {
  supporting_chunk_id?: string | null
}

/** Resolve supporting chunk for a grounding sentence (matches chunk_id or DB id). */
export function resolveSupportingChunk<T extends GroundingChunkRef>(
  sentence: GroundingSentenceRef,
  chunks: T[],
): T | undefined {
  if (!sentence.supporting_chunk_id) return undefined
  const key = sentence.supporting_chunk_id
  return chunks.find((c) => c.chunk_id === key || c.id === key)
}
