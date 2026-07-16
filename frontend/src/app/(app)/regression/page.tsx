'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GitCompare } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Panel } from '@/components/ui/panel'

interface Snapshot {
  id: string
  snapshot_label?: string
  trust_score: number
  faithfulness_avg?: number
  hallucination_rate?: number
  trace_count: number
  snapshot_at: string
}

export default function RegressionPage() {
  const [pipelineId, setPipelineId] = useState('')
  const [label, setLabel] = useState('')
  const [baselineId, setBaselineId] = useState('')
  const [compareResult, setCompareResult] = useState<{
    delta: {
      trust_score_delta: number
      regression_severity: string
      recommendation: string
      is_regression: boolean
    }
  } | null>(null)
  const [deployResult, setDeployResult] = useState<{
    passed: boolean
    trust_score: number
    baseline_trust_score: number
    regression_risk: string
    blocking_issues: string[]
  } | null>(null)
  const queryClient = useQueryClient()

  const { data: pipelines } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data),
  })

  const { data: snapshots } = useQuery({
    queryKey: ['regression-snapshots', pipelineId],
    enabled: !!pipelineId,
    queryFn: () =>
      api.get(`/regression/snapshots/${pipelineId}`).then((r) => r.data as Snapshot[]),
  })

  const createSnap = useMutation({
    mutationFn: () =>
      api
        .post(`/regression/snapshots/${pipelineId}`, { snapshot_label: label || undefined })
        .then((r) => r.data),
    onSuccess: () => {
      toast.success('Snapshot saved')
      setLabel('')
      queryClient.invalidateQueries({ queryKey: ['regression-snapshots', pipelineId] })
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Failed (Pro plan)'),
  })

  const compare = useMutation({
    mutationFn: () =>
      api
        .post('/regression/compare', {
          pipeline_id: pipelineId,
          baseline_snapshot_id: baselineId,
          compare_to: 'current',
        })
        .then((r) => r.data),
    onSuccess: (data) => {
      setCompareResult(data)
      toast.success(`Severity: ${data.delta.regression_severity}`)
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Compare failed'),
  })

  const preDeploy = useMutation({
    mutationFn: () =>
      api
        .post('/regression/pre-deploy-check', {
          pipeline_id: pipelineId,
          deploy_label: label || 'pre-deploy',
        })
        .then((r) => r.data)
        .catch((err) => {
          if (err.response?.status === 422 && err.response?.data) {
            return err.response.data
          }
          throw err
        }),
    onSuccess: (data) => {
      setDeployResult(data)
      queryClient.invalidateQueries({ queryKey: ['regression-snapshots', pipelineId] })
      if (data.passed) toast.success('Pre-deploy check passed')
      else toast.error('Pre-deploy blocked')
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Pre-deploy requires Enterprise'),
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Regression"
        description="Snapshot Trust Score baselines and run pre-deploy checks before shipping RAG changes."
      />

      <select
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm mb-6"
        value={pipelineId}
        onChange={(e) => {
          setPipelineId(e.target.value)
          setBaselineId('')
          setCompareResult(null)
          setDeployResult(null)
        }}
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
          <p className="text-sm text-muted-foreground">Snapshots are scoped per pipeline.</p>
        </Panel>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          <Panel variant="solid" title="Snapshots">
            <div className="flex flex-wrap gap-2 mb-4">
              <input
                className="bg-background border border-border rounded-lg px-3 py-2 text-sm flex-1 min-w-[140px]"
                placeholder="Label (e.g. v1.2.0-deploy)"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-lg bg-primary text-primary-foreground"
                onClick={() => createSnap.mutate()}
              >
                Save snapshot
              </button>
            </div>
            <div className="space-y-2 max-h-[360px] overflow-auto">
              {(snapshots ?? []).map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`w-full text-left rounded-lg border p-3 text-sm ${
                    baselineId === s.id ? 'border-primary' : 'border-border'
                  }`}
                  onClick={() => setBaselineId(s.id)}
                >
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <GitCompare size={12} />
                    <span>{s.snapshot_label || 'untitled'}</span>
                    <span>·</span>
                    <span>{new Date(s.snapshot_at).toLocaleString()}</span>
                  </div>
                  <p>
                    Trust {s.trust_score} · Hall {(s.hallucination_rate ?? 0).toFixed(2)} · {s.trace_count}{' '}
                    traces
                  </p>
                </button>
              ))}
              {!snapshots?.length && (
                <p className="text-sm text-muted-foreground">No snapshots yet — save a baseline.</p>
              )}
            </div>
          </Panel>

          <Panel variant="solid" title="Checks">
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-lg border border-border disabled:opacity-40"
                disabled={!baselineId}
                onClick={() => compare.mutate()}
              >
                Compare baseline → current
              </button>
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-lg border border-border"
                onClick={() => preDeploy.mutate()}
              >
                Pre-deploy check
              </button>
            </div>
            {compareResult && (
              <div className="rounded-lg border border-border p-3 text-sm mb-3">
                <p className="font-medium mb-1">
                  {compareResult.delta.is_regression ? 'Regression' : 'Stable'} ·{' '}
                  {compareResult.delta.regression_severity}
                </p>
                <p>Trust Δ {compareResult.delta.trust_score_delta}</p>
                <p className="text-muted-foreground mt-1">{compareResult.delta.recommendation}</p>
              </div>
            )}
            {deployResult && (
              <div
                className={`rounded-lg border p-3 text-sm ${
                  deployResult.passed ? 'border-emerald-700' : 'border-red-700'
                }`}
              >
                <p className="font-medium mb-1">
                  {deployResult.passed ? 'PASS' : 'BLOCK'} · risk {deployResult.regression_risk}
                </p>
                <p>
                  Trust {deployResult.trust_score} vs baseline {deployResult.baseline_trust_score}
                </p>
                {!!deployResult.blocking_issues?.length && (
                  <ul className="list-disc pl-5 mt-2 text-muted-foreground">
                    {deployResult.blocking_issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  )
}
