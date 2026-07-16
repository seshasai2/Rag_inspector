'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { downloadAuthenticatedFile } from '@/lib/download'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'
import { StatCard } from '@/components/ui/stat-card'

export default function ExecutivePage() {
  const [downloading, setDownloading] = useState(false)

  const { data: report, isLoading } = useQuery({
    queryKey: ['executive-report'],
    queryFn: () => api.get('/reports/executive', { params: { format: 'json', days: 30 } }).then((r) => r.data),
  })

  const { data: roi } = useQuery({
    queryKey: ['executive-roi'],
    queryFn: () => api.get('/reports/roi').then((r) => r.data),
  })

  const downloadPdf = async () => {
    setDownloading(true)
    try {
      await downloadAuthenticatedFile('/reports/executive', 'executive_report.pdf', {
        format: 'pdf',
        days: '30',
      })
      toast.success('PDF downloaded')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Executive"
        description="Trust, cost, and coverage for leadership — export PDF brief."
        actions={
          <button
            type="button"
            className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground disabled:opacity-40"
            disabled={downloading}
            onClick={downloadPdf}
          >
            Download PDF
          </button>
        }
      />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <StatCard label="AI Trust Score" value={`${roi?.ai_trust_score ?? report?.trust_score ?? '—'}`} color="purple" />
            <StatCard
              label="Est. business impact"
              value={`$${(roi?.estimated_business_impact_this_month ?? 0).toLocaleString()}`}
              color="amber"
            />
            <StatCard label="Hallucination rate" value={`${report?.hallucination_rate ?? '—'}`} color="red" />
          </div>
          <Panel variant="solid" title="Report payload">
            <pre className="text-xs overflow-auto max-h-96">{JSON.stringify(report, null, 2)}</pre>
          </Panel>
        </>
      )}
    </div>
  )
}
