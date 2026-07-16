'use client'

interface BM25Comparison {
  bm25_better: boolean
  top_vector_score?: number | null
  top_bm25_score?: number | null
  comparable?: boolean
  analysis: string
}

interface ScoreChunk {
  chunk_id: string
  chunk_text: string
  similarity_score?: number
  bm25_score?: number
  rank?: number
}

/** Per-query BM25 vs vector comparison (PRD F4). */
export function BM25ComparisonCard({
  comparison,
  chunks,
}: {
  comparison?: BM25Comparison | null
  chunks: ScoreChunk[]
}) {
  if (!comparison && chunks.length === 0) return null

  const comparable = comparison?.comparable !== false
    && comparison?.top_bm25_score != null
    && comparison?.top_vector_score != null

  const ranked = [...chunks]
    .filter((c) => c.bm25_score != null || c.similarity_score != null)
    .slice(0, 8)

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="font-semibold text-foreground">BM25 vs Vector</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Keyword retrieval vs embedding similarity on retrieved chunks
          </p>
        </div>
        {comparable && (
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${
              comparison!.bm25_better
                ? 'bg-purple-50 text-purple-700 border border-purple-200'
                : 'bg-blue-50 text-blue-700 border border-blue-200'
            }`}
          >
            {comparison!.bm25_better ? 'BM25 would have been better' : 'Vector performed well'}
          </span>
        )}
      </div>

      {comparable ? (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="rounded-lg bg-purple-50/80 border border-purple-100 p-3">
            <p className="text-xs text-purple-600 font-medium mb-1">Top BM25</p>
            <p className="text-2xl font-bold text-purple-700">
              {((comparison!.top_bm25_score ?? 0) * 100).toFixed(0)}
              <span className="text-sm font-medium text-purple-400">%</span>
            </p>
          </div>
          <div className="rounded-lg bg-blue-50/80 border border-blue-100 p-3">
            <p className="text-xs text-blue-600 font-medium mb-1">Top Vector</p>
            <p className="text-2xl font-bold text-blue-700">
              {((comparison!.top_vector_score ?? 0) * 100).toFixed(0)}
              <span className="text-sm font-medium text-blue-400">%</span>
            </p>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground mb-4">
          {comparison?.analysis || 'BM25 scores appear after analysis completes.'}
        </p>
      )}

      {comparison?.analysis && comparable && (
        <p className="text-sm text-foreground mb-4 leading-relaxed bg-muted/40 rounded-lg p-3">
          {comparison.analysis}
        </p>
      )}

      {ranked.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Per-chunk scores
          </p>
          {ranked.map((chunk) => {
            const vector = chunk.similarity_score ?? 0
            const bm25 = chunk.bm25_score ?? 0
            return (
              <div key={chunk.chunk_id} className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground font-mono truncate">
                    Rank {chunk.rank ?? '—'} · {chunk.chunk_id.slice(0, 16)}
                  </span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    V {(vector * 100).toFixed(0)}% · B {(bm25 * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-blue-500/80"
                    style={{ width: `${Math.min(vector * 100, 100) / 2}%` }}
                    title={`Vector ${(vector * 100).toFixed(0)}%`}
                  />
                  <div
                    className="h-full bg-purple-500/80"
                    style={{ width: `${Math.min(bm25 * 100, 100) / 2}%` }}
                    title={`BM25 ${(bm25 * 100).toFixed(0)}%`}
                  />
                </div>
                <p className="text-xs text-muted-foreground line-clamp-1">{chunk.chunk_text}</p>
              </div>
            )
          })}
          <div className="flex gap-4 text-xs text-muted-foreground pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-blue-500/80" /> Vector
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-purple-500/80" /> BM25
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
