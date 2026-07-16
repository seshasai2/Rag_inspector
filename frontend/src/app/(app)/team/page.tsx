'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

export default function TeamPage() {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('viewer')
  const queryClient = useQueryClient()

  const { data: org } = useQuery({
    queryKey: ['org-current'],
    queryFn: () => api.get('/organizations/current').then((r) => r.data),
  })

  const { data: members } = useQuery({
    queryKey: ['org-members'],
    queryFn: () => api.get('/organizations/members').then((r) => r.data),
  })

  const invite = useMutation({
    mutationFn: () => api.post('/organizations/members', { email, role }).then((r) => r.data),
    onSuccess: () => {
      toast.success('Invite sent')
      setEmail('')
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail || 'Invite failed'),
  })

  const accept = useMutation({
    mutationFn: () => api.post('/organizations/members/accept').then((r) => r.data),
    onSuccess: () => {
      toast.success('Invite accepted')
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
      queryClient.invalidateQueries({ queryKey: ['org-current'] })
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail || 'No pending invite'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/organizations/members/${id}`),
    onSuccess: () => {
      toast.success('Removed')
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
    },
  })

  const updateRole = useMutation({
    mutationFn: ({ id, nextRole }: { id: string; nextRole: string }) =>
      api.patch(`/organizations/members/${id}`, { role: nextRole }),
    onSuccess: () => {
      toast.success('Role updated')
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail || 'Update failed'),
  })

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <PageHeader
        title="Team"
        description={org ? `Workspace: ${org.name}` : 'Organization membership & RBAC'}
      />
      <div className="flex gap-2 mb-4">
        <button type="button" className="px-3 py-2 text-sm border border-border rounded-lg" onClick={() => accept.mutate()}>
          Accept pending invites
        </button>
      </div>
      <Panel variant="solid" title="Invite member">
        <div className="flex flex-wrap gap-2 mb-4">
          <input
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm flex-1"
            placeholder="email@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <select
            className="bg-background border border-border rounded-lg px-3 py-2 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {['viewer', 'analyst', 'engineer', 'admin'].map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground"
            onClick={() => invite.mutate()}
          >
            Invite
          </button>
        </div>
        <ul className="space-y-2 text-sm">
          {(members ?? []).map((m: { id: string; role: string; invited_email?: string; accepted_at?: string }) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 border border-border rounded-lg px-3 py-2">
              <span>
                {m.invited_email || m.id} · {m.accepted_at ? 'active' : 'pending'}
              </span>
              <div className="flex items-center gap-2">
                <select
                  className="bg-background border border-border rounded-lg px-2 py-1 text-xs"
                  value={m.role}
                  onChange={(e) => updateRole.mutate({ id: m.id, nextRole: e.target.value })}
                >
                  {['viewer', 'analyst', 'engineer', 'admin', 'owner'].map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <button type="button" className="text-xs text-red-400" onClick={() => remove.mutate(m.id)}>
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  )
}
