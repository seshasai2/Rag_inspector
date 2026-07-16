'use client'

import { Suspense, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'
import { authCookieOptions } from '@/lib/cookies'

function SsoCallbackInner() {
  const router = useRouter()

  useEffect(() => {
    // Prefer hash fragment handoff (avoids Referer / access-log leakage).
    const hash = typeof window !== 'undefined' ? window.location.hash.replace(/^#/, '') : ''
    const hashParams = new URLSearchParams(hash)
    const query = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
    const access = hashParams.get('access_token') || query.get('access_token')
    const refresh = hashParams.get('refresh_token') || query.get('refresh_token')
    if (access) Cookies.set('access_token', access, authCookieOptions(1 / 96))
    if (refresh) Cookies.set('refresh_token', refresh, authCookieOptions(7))
    if (typeof window !== 'undefined') {
      window.history.replaceState(null, '', '/auth/sso/callback')
    }
    router.replace('/dashboard')
  }, [router])

  return <main className="p-8 text-sm text-muted-foreground">Completing Google sign-in…</main>
}

export default function SsoCallbackPage() {
  return (
    <Suspense fallback={<main className="p-8 text-sm text-muted-foreground">Completing Google sign-in…</main>}>
      <SsoCallbackInner />
    </Suspense>
  )
}
