import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthGuard } from './auth-guard'

const replace = vi.fn()
const fetchMe = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/dashboard',
}))

vi.mock('@/components/app-shell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}))

const authState = {
  user: null as null | { id: string; name: string; email: string },
  loading: true,
  fetchMe,
}

vi.mock('@/store/auth', () => ({
  useAuthStore: () => authState,
}))

describe('AuthGuard', () => {
  beforeEach(() => {
    replace.mockClear()
    fetchMe.mockClear()
    authState.user = null
    authState.loading = true
  })

  it('shows loading state while session is resolving', () => {
    authState.loading = true
    render(
      <AuthGuard>
        <div>protected</div>
      </AuthGuard>,
    )
    expect(screen.getByTestId('auth-guard-loading')).toBeInTheDocument()
    expect(screen.queryByText('protected')).not.toBeInTheDocument()
  })

  it('redirects to login when unauthenticated', async () => {
    authState.loading = false
    authState.user = null
    render(
      <AuthGuard>
        <div>protected</div>
      </AuthGuard>,
    )
    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith('/auth/login?next=%2Fdashboard')
    })
    expect(screen.queryByText('protected')).not.toBeInTheDocument()
  })

  it('renders children when authenticated', async () => {
    authState.loading = false
    authState.user = { id: '1', name: 'Ada', email: 'ada@example.com' }
    render(
      <AuthGuard>
        <div>protected</div>
      </AuthGuard>,
    )
    expect(await screen.findByText('protected')).toBeInTheDocument()
    expect(screen.getByTestId('app-shell')).toBeInTheDocument()
    expect(replace).not.toHaveBeenCalled()
  })
})
