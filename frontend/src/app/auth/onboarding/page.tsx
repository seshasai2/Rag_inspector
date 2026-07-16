'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { useAuthStore } from '@/store/auth'

export default function OnboardingPage() {
  const router = useRouter()
  const { fetchMe } = useAuthStore()
  const [step, setStep] = useState(1)
  const [pipelineName, setPipelineName] = useState('my-first-pipeline')
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const createPipelineAndKey = async () => {
    setLoading(true)
    try {
      await api.post('/pipelines', { name: pipelineName, description: 'My first RAG pipeline' })
      const keyRes = await api.post('/keys', { name: 'Default Key' })
      setApiKey(keyRes.data.raw_key)
      setStep(2)
    } catch {
      toast.error('Setup failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const finish = async () => {
    await api.post('/auth/complete-onboarding')
    await fetchMe()
    router.push('/dashboard')
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-10">
          <div className="w-12 h-12 rounded-2xl bg-blue-500 flex items-center justify-center text-white font-bold text-xl mx-auto mb-4">R</div>
          <h1 className="text-3xl font-bold text-white">Welcome to RAGInspector</h1>
          <p className="text-white/50 mt-2">Let&apos;s get your first pipeline set up.</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-3 mb-10">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                s < step ? 'bg-green-500 text-white' : s === step ? 'bg-blue-500 text-white' : 'bg-white/10 text-white/30'
              }`}>{s < step ? '✓' : s}</div>
              {s < 3 && <div className={`w-12 h-0.5 ${s < step ? 'bg-green-500' : 'bg-white/10'}`} />}
            </div>
          ))}
        </div>

        <div className="bg-[#111118] border border-white/10 rounded-2xl p-8">
          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Name your first pipeline</h2>
              <p className="text-white/50 text-sm mb-6">This identifies your RAG application in the dashboard.</p>
              <input
                value={pipelineName}
                onChange={(e) => setPipelineName(e.target.value)}
                placeholder="customer-support-rag"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono mb-6"
              />
              <button onClick={createPipelineAndKey} disabled={loading || !pipelineName}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors">
                {loading ? 'Setting up...' : 'Create pipeline & API key →'}
              </button>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Your API key is ready</h2>
              <p className="text-white/50 text-sm mb-6">Copy this key — it won&apos;t be shown again.</p>
              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-6">
                <p className="text-xs text-green-400 mb-2 font-medium">API KEY — COPY NOW</p>
                <code className="text-green-300 font-mono text-sm break-all">{apiKey}</code>
              </div>
              <h3 className="text-white font-semibold mb-3">Install the SDK:</h3>
              <pre className="bg-white/5 border border-white/10 rounded-xl p-4 text-sm font-mono text-white/70 mb-6 overflow-x-auto">
{`pip install raginspector

from raginspector import RAGInspector
inspector = RAGInspector(
    api_key="${apiKey?.slice(0, 20)}...",
    pipeline_name="${pipelineName}"
)

@inspector.trace_retrieval
def retrieve(query): ...

@inspector.trace_generation
def generate(query, context): ...`}
              </pre>
              <button onClick={() => setStep(3)} className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-xl font-semibold transition-colors">
                I&apos;ve saved my key →
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="text-center">
              <div className="text-6xl mb-4">🚀</div>
              <h2 className="text-2xl font-bold text-white mb-3">You&apos;re all set!</h2>
              <p className="text-white/50 mb-8">Send your first trace from your RAG app, then come back to see the analysis.</p>
              <button onClick={finish} className="bg-blue-600 hover:bg-blue-500 text-white px-10 py-3 rounded-xl font-semibold transition-colors">
                Open Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
