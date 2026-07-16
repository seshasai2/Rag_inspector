import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">Back to RAGInspector</Link>
        <h1 className="text-4xl font-bold mt-8 mb-4">Privacy Policy</h1>
        <p className="text-white/50 mb-8">Last updated: June 12, 2026</p>
        <div className="space-y-6 text-white/70 leading-relaxed">
          <p>RAGInspector processes account information, API keys, billing metadata, and RAG trace data submitted by customers for observability and debugging.</p>
          <p>Trace data may include queries, retrieved chunks, generated answers, metadata, metrics, and operational logs. Customers control what they send through the SDK.</p>
          <p>We use data to operate the product, secure accounts, provide support, process billing, improve reliability, and comply with legal obligations.</p>
          <p>Production deployments should configure encryption, backups, access controls, log retention, and data deletion workflows appropriate for their customer commitments.</p>
          <p>This is a starter policy page. Before public launch, replace it with a counsel-reviewed policy that matches your actual hosting, subprocessors, retention periods, and compliance posture.</p>
        </div>
      </div>
    </main>
  )
}
