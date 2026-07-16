'use client'

import { Suspense, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth'
import { AppShell } from '@/components/app-shell'

/**
 * Client-side session gate for authenticated app routes.
 * Middleware only checks cookie presence; this validates /auth/me.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, loading, fetchMe } = useAuthStore()

  useEffect(() => {
    void fetchMe()
  }, [fetchMe])

  useEffect(() => {
    if (loading) return
    if (!user) {
      const next = encodeURIComponent(pathname || '/dashboard')
      router.replace(`/auth/login?next=${next}`)
    }
  }, [loading, user, router, pathname])

  if (loading) {
    return (
      <div
        data-testid="auth-guard-loading"
        className="min-h-screen bg-background flex items-center justify-center"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
        </div>
      }
    >
      <AppShell>{children}</AppShell>
    </Suspense>
  )
}
