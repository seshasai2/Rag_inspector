'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Radio } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

interface MonitoringConfig {
  is_enabled: boolean
  interval_minutes: number
  probe_queries: string[]
  alert_trust_threshold: number
  alert_hallucination_threshold: number
  last_run_at?: string
  next_run_at?: string
}

interface MonitoringRun {
  id: string
  trust_score?: number
  hallucination_rate?: number
  probes_run: number
  probes_failed: number
  alerts_triggered: unknown[]
  regression_detected: boolean
  run_at: string
}

export default function MonitoringPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [enabled, setEnabled] = useState(false)
  const [interval, setIntervalMin] = useState(60)
  const [probesText, setProbesText] = useState('')
  const [trustThreshold, setTrustThreshold] = useState(70)
  const [hallThreshold, setHallThreshold] = useState(0.1)
  const queryClient = useQueryClient()

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const { data: config } = useQuery({
    queryKey: ['monitoring-config', pipelineId],
    enabled: !!pipelineId,
    queryFn: () => api.get(`/monitoring/config/${pipelineId}`).then((r) => r.data as MonitoringConfig),
  })

  const { data: history } = useQuery({
    queryKey: ['monitoring-history', pipelineId],
    enabled: !!pipelineId,
    queryFn: () =>
      api.get(`/monitoring/history/${pipelineId}`, { params: { days: 7 } }).then((r) => r.data as MonitoringRun[]),
  })

  useEffect(() => {
    if (!config) return
    setEnabled(!!config.is_enabled)
    setIntervalMin(config.interval_minutes || 60)
    setProbesText((config.probe_queries || []).join('\n'))
    setTrustThreshold(config.alert_trust_threshold ?? 70)
    setHallThreshold(config.alert_hallucination_threshold ?? 0.1)
  }, [config])

  const save = useMutation({
    mutationFn: () =>
      api
        .put(`/monitoring/config/${pipelineId}`, {
          is_enabled: enabled,
          interval_minutes: interval,
          probe_queries: probesText
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean),
          alert_trust_threshold: trustThreshold,
          alert_hallucination_threshold: hallThreshold,
          alert_channels: [],
        })
        .then((r) => r.data),
    onSuccess: () => {
      toast.success('Monitoring config saved')
      queryClient.invalidateQueries({ queryKey: ['monitoring-config', pipelineId] })
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Save failed (Pro plan required)'),
  })

  const runNow = useMutation({
    mutationFn: () => api.post(`/monitoring/run-now/${pipelineId}`).then((r) => r.data),
    onSuccess: (res) => {
      toast.success(`Probe queued: ${res.run_id}`)
      queryClient.invalidateQueries({ queryKey: ['monitoring-history', pipelineId] })
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Run-now requires Enterprise'),
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Monitoring"
        description="Schedule probe evaluations against Trust Score and hallucination rate (Celery beat)."
      />

      <select
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm mb-6"
        value={pipelineId}
        onChange={(e) => setPipelineId(e.target.value)}
      >
        <option value="">Select pipeline</option>
        {(pipelines ?? []).map((p: { id: string; name: string }) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {!pipelineId ? (
        <Panel variant="solid" title="Choose a pipeline">
          <p className="text-sm text-muted-foreground">Monitoring config is per pipeline (Pro+).</p>
        </Panel>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          <Panel variant="solid" title="Config">
            <label className="flex items-center gap-2 text-sm mb-3">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              Enable monitoring
            </label>
            <label className="block text-xs text-muted-foreground mb-1">Interval (minutes)</label>
            <input
              type="number"
              min={1}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm mb-3"
              value={interval}
              onChange={(e) => setIntervalMin(Number(e.target.value))}
            />
            <label className="block text-xs text-muted-foreground mb-1">Probe queries (one per line)</label>
            <textarea
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm mb-3 min-h-[100px]"
              value={probesText}
              onChange={(e) => setProbesText(e.target.value)}
              placeholder="What is the refund policy?"
            />
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Trust alert below</label>
                <input
                  type="number"
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm"
                  value={trustThreshold}
                  onChange={(e) => setTrustThreshold(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Hallucination alert above</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm"
                  value={hallThreshold}
                  onChange={(e) => setHallThreshold(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground"
                onClick={() => save.mutate()}
              >
                Save
              </button>
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-lg border border-border"
                onClick={() => runNow.mutate()}
              >
                Run now
              </button>
            </div>
            {(config?.last_run_at || config?.next_run_at) && (
              <p className="text-xs text-muted-foreground mt-3">
                Last: {config.last_run_at || '—'} · Next: {config.next_run_at || '—'}
              </p>
            )}
          </Panel>

          <Panel variant="solid" title="Recent runs (7d)">
            {!history?.length ? (
              <p className="text-sm text-muted-foreground">No runs yet. Enable config or Run now.</p>
            ) : (
              <div className="space-y-2 max-h-[420px] overflow-auto">
                {history.map((run) => (
                  <div key={run.id} className="rounded-lg border border-border p-3 text-sm">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                      <Radio size={12} />
                      <span>{new Date(run.run_at).toLocaleString()}</span>
                      {run.regression_detected && <span className="text-amber-500">regression</span>}
                    </div>
                    <p>
                      Trust {run.trust_score ?? '—'} · Hall {(run.hallucination_rate ?? 0).toFixed(2)} · Probes{' '}
                      {run.probes_failed}/{run.probes_run} failed
                    </p>
                    {!!run.alerts_triggered?.length && (
                      <p className="text-xs text-red-400 mt-1">{run.alerts_triggered.length} alert(s)</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  )
}
