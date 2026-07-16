'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { resolveSupportingChunk } from '@/lib/grounding'

export interface GroundingChunk {
  id: string
  chunk_id: string
  chunk_text: string
  similarity_score?: number
  bm25_score?: number
  rank?: number
  was_cited: boolean
}

export interface GroundingSentence {
  sentence_text: string
  sentence_index: number
  is_grounded: boolean
  supporting_chunk_id?: string
  confidence_score?: number
}

export { resolveSupportingChunk } from '@/lib/grounding'

function chunkSupportsSentence(
  chunk: GroundingChunk,
  sentence: GroundingSentence | null,
): boolean {
  if (!sentence?.supporting_chunk_id) return false
  const key = sentence.supporting_chunk_id
  return chunk.chunk_id === key || chunk.id === key
}

/**
 * PRD key-page behavior: sentence-level grounding with hover → supporting chunk.
 */
export function GroundingAttributionPanel({
  sentences,
  chunks,
  groundedFraction,
  isHallucination,
  fallbackAnswer,
}: {
  sentences: GroundingSentence[]
  chunks: GroundingChunk[]
  groundedFraction?: number | null
  isHallucination?: boolean | null
  fallbackAnswer?: string
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const [pinnedIndex, setPinnedIndex] = useState<number | null>(null)
  const chunkRefs = useRef<Record<string, HTMLDivElement | null>>({})

  const activeIndex = pinnedIndex ?? hoveredIndex
  const activeSentence =
    activeIndex != null
      ? sentences.find((s) => s.sentence_index === activeIndex) ?? null
      : null
  const activeChunk = activeSentence
    ? resolveSupportingChunk(activeSentence, chunks)
    : undefined

  const scrollChunkIntoView = useCallback((chunk: GroundingChunk | undefined) => {
    if (!chunk) return
    const el = chunkRefs.current[chunk.chunk_id] ?? chunkRefs.current[chunk.id]
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [])

  useEffect(() => {
    if (activeChunk) scrollChunkIntoView(activeChunk)
  }, [activeChunk, scrollChunkIntoView])

  const groundedCount = useMemo(
    () => sentences.filter((s) => s.is_grounded).length,
    [sentences],
  )

  if (sentences.length === 0) {
    return (
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="font-semibold text-foreground mb-4">LLM Answer — Sentence Grounding</h2>
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap bg-muted/30 rounded-lg p-3">
          {fallbackAnswer || 'No answer text.'}
        </p>
        <p className="text-xs text-muted-foreground mt-3">
          Grounding results appear after analysis completes.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="font-semibold text-foreground">Sentence Grounding</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Hover a sentence to highlight its supporting chunk · click to pin
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {groundedCount}/{sentences.length} grounded
            {groundedFraction != null ? ` · ${(groundedFraction * 100).toFixed(0)}%` : ''}
          </span>
          {isHallucination != null && (
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                isHallucination ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
              }`}
            >
              {isHallucination ? '⚠ Hallucination detected' : '✓ Grounded'}
            </span>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Answer sentences */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Answer
          </h3>
          <div className="space-y-2 max-h-[28rem] overflow-y-auto pr-1">
            {sentences.map((gr) => {
              const support = resolveSupportingChunk(gr, chunks)
              const isActive = activeIndex === gr.sentence_index
              return (
                <button
                  key={gr.sentence_index}
                  type="button"
                  onMouseEnter={() => setHoveredIndex(gr.sentence_index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  onFocus={() => setHoveredIndex(gr.sentence_index)}
                  onBlur={() => setHoveredIndex(null)}
                  onClick={() =>
                    setPinnedIndex((prev) =>
                      prev === gr.sentence_index ? null : gr.sentence_index,
                    )
                  }
                  className={`w-full text-left relative p-2.5 rounded-lg border-l-4 text-sm leading-relaxed transition-all outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                    gr.is_grounded
                      ? 'border-l-green-400 bg-green-50/60 text-foreground'
                      : 'border-l-red-400 bg-red-50/60 text-foreground'
                  } ${
                    isActive
                      ? 'ring-2 ring-blue-400/60 shadow-sm scale-[1.01]'
                      : 'hover:brightness-[0.98]'
                  }`}
                  aria-pressed={pinnedIndex === gr.sentence_index}
                  aria-describedby={
                    isActive && support ? `support-preview-${gr.sentence_index}` : undefined
                  }
                >
                  <span
                    className={`mr-1.5 text-xs font-bold ${
                      gr.is_grounded ? 'text-green-500' : 'text-red-500'
                    }`}
                  >
                    {gr.is_grounded ? '✓' : '✗'}
                  </span>
                  {gr.sentence_text}
                  {gr.confidence_score != null && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({(gr.confidence_score * 100).toFixed(0)}%)
                    </span>
                  )}

                  {/* Hover / pin tooltip: supporting chunk preview */}
                  {isActive && (
                    <div
                      id={`support-preview-${gr.sentence_index}`}
                      className="mt-2 p-2 rounded-md bg-slate-900 text-slate-100 text-xs leading-relaxed shadow-lg"
                      role="tooltip"
                    >
                      {gr.is_grounded && support ? (
                        <>
                          <p className="font-semibold text-green-300 mb-1">
                            Supporting chunk · rank {support.rank ?? '—'}
                            {support.similarity_score != null
                              ? ` · vector ${(support.similarity_score * 100).toFixed(0)}%`
                              : ''}
                          </p>
                          <p className="text-slate-200 line-clamp-4">{support.chunk_text}</p>
                          <p className="mt-1 font-mono text-slate-400 truncate">
                            {support.chunk_id}
                          </p>
                        </>
                      ) : gr.is_grounded ? (
                        <p className="text-amber-200">
                          Marked grounded but supporting chunk was not found in retrieved set.
                        </p>
                      ) : (
                        <p className="text-red-200">
                          Not grounded in retrieved context — no supporting chunk.
                        </p>
                      )}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
          <div className="flex flex-wrap gap-4 mt-3">
            <span className="text-xs text-green-600">✓ Green = grounded in context</span>
            <span className="text-xs text-red-600">✗ Red = potential hallucination</span>
          </div>
        </div>

        {/* Retrieved chunks — highlight on sentence hover */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Retrieved Chunks ({chunks.length})
          </h3>
          <div className="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
            {chunks.length === 0 ? (
              <p className="text-muted-foreground text-sm">No chunks retrieved.</p>
            ) : (
              chunks.map((chunk, i) => {
                const isSupport = chunkSupportsSentence(chunk, activeSentence)
                return (
                  <div
                    key={chunk.id}
                    ref={(el) => {
                      chunkRefs.current[chunk.chunk_id] = el
                      chunkRefs.current[chunk.id] = el
                    }}
                    data-testid={`chunk-card-${chunk.chunk_id}`}
                    data-highlighted={isSupport ? 'true' : 'false'}
                    className={`border rounded-xl p-4 transition-all duration-200 ${
                      isSupport
                        ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-300/70 shadow-md'
                        : chunk.was_cited
                          ? 'border-green-200 bg-green-50/50'
                          : 'border-border bg-muted/20'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="text-xs font-medium text-muted-foreground">
                        Rank {chunk.rank ?? i + 1}
                      </span>
                      {isSupport && (
                        <span className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                          ← Supports hovered sentence
                        </span>
                      )}
                      {chunk.was_cited && !isSupport && (
                        <span className="text-xs font-semibold text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                          ✓ Cited
                        </span>
                      )}
                      {chunk.similarity_score != null && (
                        <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full font-medium">
                          Vector: {(chunk.similarity_score * 100).toFixed(0)}%
                        </span>
                      )}
                      {chunk.bm25_score != null && (
                        <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full font-medium">
                          BM25: {(chunk.bm25_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p
                      className={`text-sm text-foreground leading-relaxed ${
                        isSupport ? '' : 'line-clamp-3'
                      }`}
                    >
                      {chunk.chunk_text}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground font-mono truncate">
                      {chunk.chunk_id}
                    </p>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
