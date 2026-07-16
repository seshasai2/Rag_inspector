import Link from 'next/link'

export default function RefundPolicyPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">Back to RAGInspector</Link>
        <h1 className="text-4xl font-bold mt-8 mb-4">Refund and Cancellation Policy</h1>
        <p className="text-white/50 mb-8">Last updated: June 12, 2026</p>
        <div className="space-y-6 text-white/70 leading-relaxed">
          <p>Subscriptions can be cancelled from the billing settings page. Cancellation takes effect at the end of the current billing period unless otherwise stated in a signed agreement.</p>
          <p>Refunds are reviewed case by case for duplicate charges, billing errors, or service-impacting incidents. Usage-based overages, if introduced later, may be non-refundable after processing.</p>
          <p>Enterprise contracts may include separate cancellation, refund, and service credit terms.</p>
          <p>Before accepting payments publicly, replace this starter policy with terms reviewed for your jurisdiction, payment provider, and customer segment.</p>
        </div>
      </div>
    </main>
  )
}
