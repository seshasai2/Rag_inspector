'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Activity,
  BarChart3,
  Boxes,
  ChevronLeft,
  ChevronRight,
  Database,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Shield,
  BookOpen,
  Briefcase,
  FileText,
  FlaskConical,
  GitCompare,
  LineChart,
  MessageSquare,
  Radio,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { usePipelineId, usePipelines } from '@/hooks/usePipelineId'
import { ThemeToggle } from '@/components/theme-toggle'
import { cn } from '@/lib/utils'

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/queries', label: 'Queries', icon: Activity },
  { href: '/chunks', label: 'Chunks', icon: Database },
  { href: '/knowledge/gaps', label: 'Gaps', icon: BookOpen },
  { href: '/autofix', label: 'Fixes', icon: Wrench },
  { href: '/documents', label: 'Docs', icon: FileText },
  { href: '/monitoring', label: 'Monitor', icon: Radio },
  { href: '/regression', label: 'Regression', icon: GitCompare },
  { href: '/benchmark', label: 'Benchmark', icon: LineChart },
  { href: '/studio', label: 'Studio', icon: FlaskConical },
  { href: '/investigator', label: 'Investigator', icon: MessageSquare },
  { href: '/executive', label: 'Executive', icon: Briefcase },
  { href: '/team', label: 'Team', icon: Users },
  { href: '/metrics', label: 'Metrics', icon: BarChart3 },
  { href: '/pipelines', label: 'Pipelines', icon: GitBranch },
  { href: '/settings', label: 'Settings', icon: Settings },
]

function NavLinks({
  pathname,
  withPipeline,
  onNavigate,
  collapsed,
}: {
  pathname: string
  withPipeline: (href: string) => string
  onNavigate?: () => void
  collapsed: boolean
}) {
  return (
    <>
      {NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
        const Icon = item.icon
        return (
          <Link
            key={item.href}
            href={withPipeline(item.href)}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors',
              active
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted',
            )}
            title={item.label}
            aria-current={active ? 'page' : undefined}
          >
            <Icon size={16} className="shrink-0" aria-hidden />
            {!collapsed && <span>{item.label}</span>}
          </Link>
        )
      })}
    </>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { pipelineId, setPipelineId, withPipeline } = usePipelineId()
  const { data: pipelines } = usePipelines()

  const handleLogout = () => {
    logout()
    router.replace('/auth/login')
  }

  const sidebar = (
    <>
      <div className="h-14 px-3 flex items-center gap-2 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
          <Shield size={16} aria-hidden />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">RAGInspector</p>
            <p className="text-[10px] text-muted-foreground truncate">Pipeline debugger</p>
          </div>
        )}
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto" aria-label="Primary">
        <NavLinks
          pathname={pathname}
          withPipeline={withPipeline}
          collapsed={collapsed}
          onNavigate={() => setMobileOpen(false)}
        />
      </nav>

      <div className="p-2 border-t border-border space-y-2">
        {!collapsed && (
          <div>
            <label
              htmlFor="shell-pipeline"
              className="text-[10px] uppercase tracking-wide text-muted-foreground px-1"
            >
              Pipeline
            </label>
            <select
              id="shell-pipeline"
              value={pipelineId || ''}
              onChange={(e) => setPipelineId(e.target.value || undefined)}
              className="mt-1 w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs text-foreground"
            >
              <option value="">All pipelines</option>
              {pipelines?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="hidden md:flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-muted-foreground hover:bg-muted"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          {!collapsed && 'Collapse'}
        </button>
        <div className={cn('flex items-center gap-2', collapsed ? 'justify-center' : '')}>
          <ThemeToggle className={collapsed ? '' : 'shrink-0'} />
          {!collapsed && (
            <span className="text-[10px] text-muted-foreground">Theme</span>
          )}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-muted-foreground hover:text-accent-red hover:bg-accent-red/10"
        >
          <LogOut size={14} />
          {!collapsed && (user?.name || 'Log out')}
        </button>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 h-14 border-b border-border bg-card flex items-center px-3 gap-3">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="p-2 rounded-lg hover:bg-muted text-foreground"
          aria-label="Open navigation"
        >
          <Menu size={18} />
        </button>
        <span className="text-sm font-semibold flex-1">RAGInspector</span>
        <ThemeToggle />
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative z-10 w-64 h-full bg-card border-r border-border flex flex-col">
            <div className="absolute top-3 right-3">
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="p-2 rounded-lg hover:bg-muted"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
            {sidebar}
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden md:flex sticky top-0 h-screen border-r border-border bg-card flex-col transition-all',
          collapsed ? 'w-[68px]' : 'w-56',
        )}
      >
        {sidebar}
      </aside>

      <main className="flex-1 min-w-0 pt-14 md:pt-0">{children}</main>
    </div>
  )
}

export function EmptyState({
  icon: Icon = Boxes,
  title,
  description,
}: {
  icon?: React.ElementType
  title: string
  description: string
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
      <Icon className="mb-3 opacity-30" size={36} aria-hidden />
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="text-xs mt-1 max-w-sm">{description}</p>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
  title = 'Something went wrong',
}: {
  message: string
  onRetry?: () => void
  title?: string
}) {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 text-center px-4"
      role="alert"
    >
      <p className="text-sm text-accent-red font-medium">{title}</p>
      <p className="text-xs text-muted-foreground mt-1 max-w-sm">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-xs px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-foreground"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      className="flex items-center justify-center py-16 text-muted-foreground text-sm gap-3"
      role="status"
      aria-live="polite"
    >
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      {label}
    </div>
  )
}
