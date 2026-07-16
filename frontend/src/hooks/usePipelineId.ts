'use client'

import { useCallback, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface PipelineSummary {
  id: string
  name: string
}

/** Shared pipelines list (React Query cache key: ['pipelines']). */
export function usePipelines() {
  return useQuery({
    queryKey: ['pipelines'],
    queryFn: () => api.get('/pipelines').then((r) => r.data as PipelineSummary[]),
    staleTime: 60_000,
  })
}

/**
 * URL-driven pipeline scope shared by AppShell and feature pages.
 * Prefer this over local useState for pipeline filters.
 */
export function usePipelineId() {
  const searchParams = useSearchParams()
  const pathname = usePathname()
  const router = useRouter()
  const pipelineId = searchParams.get('pipeline_id') || undefined

  const setPipelineId = useCallback(
    (id: string | undefined | null) => {
      const params = new URLSearchParams(searchParams.toString())
      if (id) params.set('pipeline_id', id)
      else params.delete('pipeline_id')
      const qs = params.toString()
      router.push(qs ? `${pathname}?${qs}` : pathname)
    },
    [pathname, router, searchParams],
  )

  const withPipeline = useCallback(
    (href: string) => {
      if (!pipelineId) return href
      const [path, existing] = href.split('?')
      const params = new URLSearchParams(existing || '')
      params.set('pipeline_id', pipelineId)
      return `${path}?${params.toString()}`
    },
    [pipelineId],
  )

  return useMemo(
    () => ({ pipelineId, setPipelineId, withPipeline }),
    [pipelineId, setPipelineId, withPipeline],
  )
}
