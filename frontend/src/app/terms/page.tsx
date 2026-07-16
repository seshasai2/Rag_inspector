import Link from 'next/link'

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">Back to RAGInspector</Link>
        <h1 className="text-4xl font-bold mt-8 mb-4">Terms of Service</h1>
        <p className="text-white/50 mb-8">Last updated: June 12, 2026</p>
        <div className="space-y-6 text-white/70 leading-relaxed">
          <p>These terms govern access to RAGInspector. By using the service, you agree to use it lawfully and only with data you are authorized to process.</p>
          <p>You are responsible for your account credentials, API keys, user content, and RAG trace data. Do not submit regulated, sensitive, or personal data unless your deployment and agreements support that use.</p>
          <p>Paid plans renew according to the billing period shown at checkout. We may suspend access for abuse, unpaid invoices, security risk, or violations of these terms.</p>
          <p>The service is provided as-is except where a signed agreement says otherwise. RAGInspector helps identify RAG quality issues, but you remain responsible for production AI behavior and customer-facing outputs.</p>
          <p>For commercial deployment, replace this starter policy with counsel-reviewed terms tailored to your company, jurisdiction, and data processing commitments.</p>
        </div>
      </div>
    </main>
  )
}
