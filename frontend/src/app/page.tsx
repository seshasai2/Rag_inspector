'use client'
import Link from 'next/link'
import { useState } from 'react'

export default function LandingPage() {
  const [usersPerDay, setUsersPerDay] = useState(1000)
  const [costPerError, setCostPerError] = useState(50)
  const estimatedMonthlyCost = (usersPerDay * 0.05 * costPerError * 30).toLocaleString()

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Nav */}
      <nav className="border-b border-white/10 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white font-bold text-sm">R</div>
            <span className="font-semibold text-lg">RAGInspector</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth/login" className="text-sm text-white/60 hover:text-white transition-colors">Sign in</Link>
            <Link href="/auth/register" className="text-sm bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg transition-colors font-medium">
              Monitor My First 100 Queries Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 rounded-full px-3 py-1 mb-8">
          <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse"></span>
          Hallucination Detection · Root Cause in 30s
        </div>
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight">
          Your AI Chatbot Is<br />
          <span className="text-red-400">Confidently Making Things Up</span><br />
          Are You Watching?
        </h1>
        <p className="text-xl text-white/50 mb-10 max-w-3xl mx-auto leading-relaxed">
          RAGInspector monitors every answer your AI gives — checking if it is actually supported
          by your documents or just hallucinated. When something is wrong, find the exact
          failure point in 30 seconds.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link href="/auth/register" className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-all hover:scale-105">
            Monitor My First 100 Queries Free
          </Link>
          <a href="https://github.com/raginspector/raginspector" className="border border-white/20 hover:border-white/40 text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-all">
            View on GitHub
          </a>
        </div>

        {/* Hallucination Cost Calculator */}
        <div className="mt-12 bg-[#111118] border border-white/10 rounded-2xl p-6 max-w-xl mx-auto text-left">
          <h3 className="font-semibold text-blue-400 mb-4 text-sm uppercase tracking-wide">Hallucination Cost Calculator</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-white/60 block mb-1">How many users does your AI chatbot serve per day?</label>
              <input
                type="number"
                value={usersPerDay}
                onChange={e => setUsersPerDay(Number(e.target.value) || 0)}
                className="w-full bg-[#1a1a24] border border-white/10 rounded-lg px-4 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                // Browser password/form extensions inject attrs like fdprocessedid before hydrate.
                suppressHydrationWarning
              />
            </div>
            <div>
              <label className="text-sm text-white/60 block mb-1">What is one wrong answer worth in customer support cost?</label>
              <input
                type="number"
                value={costPerError}
                onChange={e => setCostPerError(Number(e.target.value) || 0)}
                className="w-full bg-[#1a1a24] border border-white/10 rounded-lg px-4 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                suppressHydrationWarning
              />
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <p className="text-sm text-white/60">Estimated monthly cost of undetected hallucinations:</p>
              <p className="text-2xl font-bold text-red-400 mt-1">₹{estimatedMonthlyCost}</p>
              <p className="text-xs text-white/30 mt-1">Assuming 5% hallucination rate</p>
            </div>
          </div>
        </div>

        {/* Code snippet */}
        <div className="mt-12 bg-[#111118] border border-white/10 rounded-2xl p-6 text-left max-w-2xl mx-auto">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500/70"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/70"></div>
            <div className="w-3 h-3 rounded-full bg-green-500/70"></div>
            <span className="text-white/30 text-xs ml-2 font-mono">your_rag.py</span>
          </div>
          <pre className="text-sm font-mono text-white/80 overflow-x-auto leading-relaxed">
{`from raginspector import RAGInspector

inspector = RAGInspector(
    api_key="ri-...",
    pipeline_name="customer-support"
)

@inspector.trace_retrieval
def retrieve(query: str) -> list[dict]:
    return vector_db.search(query, k=5)

@inspector.trace_generation
def generate(query: str, context: list) -> str:
    return llm.complete(query, context)`}
          </pre>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-16">Everything you need to debug RAG</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: '🔍',
              title: 'Sentence-level grounding',
              desc: 'See exactly which sentences in the LLM response are hallucinated vs grounded in retrieved context.',
            },
            {
              icon: '📊',
              title: 'AI Trustworthiness Score',
              desc: 'A single 0-100 score your customer success team can put in QBRs. No RAG expertise needed.',
            },
            {
              icon: '💡',
              title: 'Automated Fix Recommendations',
              desc: '"Add more documentation on returns — 34 queries had coverage gaps here." Actionable, not just raw data.',
            },
            {
              icon: '⚡',
              title: 'Automatic failure classification',
              desc: 'retrieval_miss, hallucination, coverage_gap, chunking_issue — classified automatically with recommendations.',
            },
            {
              icon: '🆚',
              title: 'BM25 vs Vector comparison',
              desc: 'Detect when keyword search would outperform your vector retrieval and why.',
            },
            {
              icon: '🔔',
              title: 'Slack Alerts (Free)',
              desc: '"🚨 Your AI hallucination rate spiked to 12% today." Free Slack webhooks, no subscription needed.',
            },
          ].map((f) => (
            <div key={f.title} className="bg-[#111118] border border-white/10 rounded-xl p-6 hover:border-blue-500/30 transition-colors">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-semibold mb-2 text-lg">{f.title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing — single plan, both INR and USD */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4">Simple pricing</h2>
        <p className="text-center text-white/50 mb-16">Start free. Upgrade when you need more. <span className="text-white/30 text-sm ml-2">INR · USD</span></p>
        <div className="grid md:grid-cols-4 gap-6">
          {[
            {
              name: 'Free', price: '₹0 · $0',
              features: ['100 queries/month', 'Full instrumentation', 'Sentence-level grounding', 'No credit card'],
              cta: 'Get started', href: '/auth/register', highlight: false,
            },
            {
              name: 'Starter', price: '₹1,999/mo · $24/mo',
              features: ['10,000 queries/month', 'Trustworthiness dashboard', 'Slack hallucination alerts', '90-day history'],
              cta: 'Start Free', href: '/auth/register', highlight: false,
            },
            {
              name: 'Pro', price: '₹5,999/mo · $69/mo',
              features: ['100,000 queries/month', 'BM25 vs Vector comparison', 'Fix suggestions (as analyzed)', 'Higher history limits'],
              cta: 'Start Pro', href: '/auth/register', highlight: true,
            },
            {
              name: 'Enterprise', price: '₹14,999/mo · $179/mo',
              features: ['Unlimited traces (config)', 'Org / audit APIs', 'Roadmap: SSO & on-prem (Phase 10)', 'Billing skeleton today'],
              cta: 'Start free', href: '/auth/register', highlight: false,
            },
          ].map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl p-8 border ${plan.highlight ? 'bg-blue-600 border-blue-500' : 'bg-[#111118] border-white/10'}`}
            >
              <h3 className="font-bold text-xl mb-1">{plan.name}</h3>
              <p className="text-3xl font-bold mb-6">{plan.price}</p>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <span className={plan.highlight ? 'text-blue-200' : 'text-blue-400'}>✓</span>
                    <span className={plan.highlight ? 'text-blue-50' : 'text-white/70'}>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`block text-center py-3 rounded-xl font-semibold transition-all ${
                  plan.highlight
                    ? 'bg-white text-blue-600 hover:bg-blue-50'
                    : 'border border-white/20 hover:border-white/40 text-white'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="text-center text-white/20 text-xs mt-8">Billed via Razorpay. Pay in INR (UPI/Cards/Netbanking) or USD (International Cards).</p>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-8 text-center text-white/30 text-sm">
        <p>© 2026 RAGInspector v2.0. Built for teams building with LLMs. All metrics run on free, open-source tools.</p>
        <div className="mt-4 flex items-center justify-center gap-4">
          <Link href="/terms" className="hover:text-white/60">Terms</Link>
          <Link href="/privacy" className="hover:text-white/60">Privacy</Link>
          <Link href="/refund-policy" className="hover:text-white/60">Refunds</Link>
        </div>
      </footer>
    </div>
  )
}
