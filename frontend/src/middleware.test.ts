import { describe, expect, it } from 'vitest'
import { NextRequest } from 'next/server'
import { middleware } from './middleware'

function makeRequest(path: string, cookies: Record<string, string> = {}) {
  const headers = new Headers()
  const cookieHeader = Object.entries(cookies)
    .map(([k, v]) => `${k}=${v}`)
    .join('; ')
  if (cookieHeader) headers.set('cookie', cookieHeader)
  return new NextRequest(new URL(path, 'http://localhost:3000'), { headers })
}

describe('auth middleware guard', () => {
  it('redirects to login when no auth cookies are present', () => {
    const res = middleware(makeRequest('/dashboard'))
    expect(res.status).toBe(307)
    const location = res.headers.get('location')!
    expect(location).toContain('/auth/login')
    expect(location).toContain('next=%2Fdashboard')
  })

  it('preserves path and query in next param', () => {
    const res = middleware(makeRequest('/queries?failure_type=hallucination'))
    const location = res.headers.get('location')!
    expect(decodeURIComponent(location)).toContain(
      'next=/queries?failure_type=hallucination',
    )
  })

  it('allows request when access_token cookie is present', () => {
    const res = middleware(makeRequest('/dashboard', { access_token: 'tok' }))
    expect(res.status).toBe(200)
    expect(res.headers.get('location')).toBeNull()
  })

  it('allows request when only refresh_token cookie is present', () => {
    const res = middleware(makeRequest('/settings', { refresh_token: 'ref' }))
    expect(res.status).toBe(200)
  })
})
