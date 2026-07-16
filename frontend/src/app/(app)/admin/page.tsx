'use client'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'
import { StatCard } from '@/components/ui/stat-card'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Users, Webhook } from 'lucide-react'

export default function AdminPage() {
  const { data: summary } = useQuery({ queryKey: ['admin-summary'], queryFn: () => api.get('/admin/summary').then(r => r.data) })
  const { data: users } = useQuery({ queryKey: ['admin-users'], queryFn: () => api.get('/admin/users').then(r => r.data) })
  const { data: failedJobs } = useQuery({ queryKey: ['admin-failed-jobs'], queryFn: () => api.get('/admin/failed-jobs').then(r => r.data) })
  const { data: webhooks } = useQuery({ queryKey: ['admin-webhooks'], queryFn: () => api.get('/admin/webhooks').then(r => r.data) })

  return (
    <main className="p-6 max-w-6xl mx-auto">
      <PageHeader title="Support Admin" />
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <StatCard label="Users" value={summary?.users ?? 0} icon={Users} color="blue" />
        <StatCard label="Failed jobs" value={summary?.failed_jobs ?? 0} icon={AlertTriangle} color="red" />
        <StatCard label="Recent webhooks" value={webhooks?.length ?? 0} icon={Webhook} color="blue" />
      </div>
      <Panel variant="solid" title="Recent Users" className="mb-4">
        <div className="space-y-2">
          {users?.slice(0, 10).map((u: any) => (
            <div key={u.id} className="text-sm border-b border-border pb-2">
              {u.email} · {u.subscription_plan} · {u.email_verified ? 'verified' : 'unverified'}
            </div>
          ))}
        </div>
      </Panel>
      <Panel variant="solid" title="Failed Jobs">
        <div className="space-y-2">
          {failedJobs?.slice(0, 10).map((j: any) => (
            <div key={j.id} className="text-sm border-b border-border pb-2">
              {j.trace_id} · {j.error_message}
            </div>
          ))}
        </div>
      </Panel>
    </main>
  )
}
