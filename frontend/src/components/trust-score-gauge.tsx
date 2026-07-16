'use client'

import { Shield } from 'lucide-react'

/** Dashboard hero metric: aggregate Trust Score (0–100). */
export function TrustScoreGauge({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444'
  const bgColor =
    score >= 80
      ? 'bg-green-500/10 text-green-400 border-green-500/20'
      : score >= 60
        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        : 'bg-red-500/10 text-red-400 border-red-500/20'

  return (
    <div
      data-testid="trust-score-gauge"
      className="bg-gradient-to-br from-slate-900/50 to-slate-800/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 col-span-2 lg:col-span-1 relative overflow-hidden"
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl" />
      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-slate-400 font-medium">Trust Score</p>
          <div className={`w-10 h-10 rounded-xl ${bgColor} border flex items-center justify-center`}>
            <Shield size={18} />
          </div>
        </div>
        <div className="flex items-end gap-3 mb-4">
          <p className="text-5xl font-bold text-white" style={{ color }} data-testid="trust-score-value">
            {score}
          </p>
          <p className="text-xl text-slate-400 mb-2">/100</p>
        </div>
        <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out relative"
            style={{ width: `${Math.min(score, 100)}%`, backgroundColor: color }}
            data-testid="trust-score-bar"
          >
            <div className="absolute inset-0 bg-white/20 animate-pulse" />
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-3 leading-relaxed">
          {score >= 80
            ? 'Your AI is highly trustworthy. Answers are well-grounded and reliable.'
            : score >= 60
              ? 'Your AI has moderate trustworthiness. Review highlighted failures for improvement.'
              : 'Your AI may be generating unreliable answers. Investigate failures immediately.'}
        </p>
      </div>
    </div>
  )
}
