import { describe, expect, it } from 'vitest'
import { cn } from '@/lib/utils'
import { getApiErrorMessage } from '@/lib/errors'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('px-2', 'py-1')).toContain('px-2')
    expect(cn('px-2', false && 'hidden', 'text-sm')).toContain('text-sm')
  })
})

describe('getApiErrorMessage', () => {
  it('returns fallback for empty input', () => {
    expect(getApiErrorMessage(null)).toBe('Request failed')
  })

  it('prefers string detail', () => {
    const err = {
      response: { data: { detail: 'Invalid credentials' }, status: 401 },
      message: 'Request failed',
    }
    expect(getApiErrorMessage(err)).toBe('Invalid credentials')
  })

  it('formats object detail with code', () => {
    const err = {
      response: { data: { detail: { message: 'Bad plan', code: 'plan_forbidden' } }, status: 403 },
      message: 'x',
    }
    expect(getApiErrorMessage(err)).toBe('Bad plan (plan_forbidden)')
  })

  it('handles network error message', () => {
    expect(getApiErrorMessage({ message: 'Network Error' })).toMatch(/Network error/)
  })
})
