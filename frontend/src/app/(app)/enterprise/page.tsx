'use client'

import Link from 'next/link'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

/**
 * Phase 9.7 — Enterprise Console quarantined.
 * SSO tiles and Phase-10 product claims were overselling unfinished work.
 * Real org/audit APIs remain under Settings / API docs; SaaS features are ROADMAP Phase 10.
 */
export default function EnterprisePage() {
  return (
    <main className="p-6 max-w-3xl mx-auto">
      <PageHeader
        title="Enterprise Console"
        description="This surface is quarantined so the portfolio demo stays honest."
      />
      <Panel variant="solid" title="Not a shipped product page">
        <p className="text-sm text-muted-foreground mb-4">
          Identity SSO tiles, knowledge-gap automation, and similar enterprise claims are
          deferred to <strong>ROADMAP Phase 10</strong>. They are documented as experimental
          stubs — not production features.
        </p>
        <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-2 mb-6">
          <li>
            Working core demo: <Link className="text-primary hover:underline" href="/queries">Queries</Link> (sentence grounding)
          </li>
          <li>
            Scope matrix: see repo <code className="text-foreground">docs/IMPLEMENTED.md</code>
          </li>
          <li>
            Org members / audit / webhooks: use Settings and the API — not this marketing shell
          </li>
        </ul>
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Back to dashboard
        </Link>
      </Panel>
    </main>
  )
}
