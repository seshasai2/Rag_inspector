import type { AxiosError } from 'axios'

/** Normalize API error payloads into a user-facing message (no stack traces). */
export function getApiErrorMessage(error: unknown, fallback = 'Request failed'): string {
  if (!error || typeof error !== 'object') return fallback
  const ax = error as AxiosError<{ detail?: unknown }>
  const detail = ax.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object') {
    const d = detail as { message?: string; code?: string }
    if (d.message) return d.code ? `${d.message} (${d.code})` : d.message
  }
  if (ax.response?.status === 429) return 'Rate limit exceeded. Try again shortly.'
  if (ax.response?.status === 403) return 'You do not have permission for this action.'
  if (ax.response?.status === 404) return 'Resource not found.'
  if (ax.response?.status && ax.response.status >= 500) {
    return 'Server error. Retry or check system health.'
  }
  if (ax.message === 'Network Error') return 'Network error. Check your connection.'
  return fallback
}
