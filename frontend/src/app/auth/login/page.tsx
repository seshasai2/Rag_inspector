'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/auth'
import api from '@/lib/api'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

function safeInternalPath(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//')) {
    return '/dashboard'
  }
  return next
}

export default function LoginPage() {
  const { login, completeMfaLogin } = useAuthStore()
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [needsVerification, setNeedsVerification] = useState(false)
  const [resending, setResending] = useState(false)
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [rememberDevice, setRememberDevice] = useState(false)

  const { register, handleSubmit, getValues, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const goNext = () => {
    const next = new URLSearchParams(window.location.search).get('next')
    router.push(safeInternalPath(next))
  }

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    setNeedsVerification(false)
    try {
      const result = await login(data.email, data.password)
      if (result.mfaRequired) {
        setMfaToken(result.mfaToken)
        toast('Enter your authenticator code')
        return
      }
      toast.success('Welcome back!')
      goNext()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed'
      if (typeof msg === 'string' && msg.toLowerCase().includes('email not verified')) {
        setNeedsVerification(true)
      }
      toast.error(typeof msg === 'string' ? msg : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const onMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mfaToken || !mfaCode.trim()) {
      toast.error('Enter your MFA code')
      return
    }
    setLoading(true)
    try {
      await completeMfaLogin(mfaToken, mfaCode.trim(), rememberDevice)
      toast.success('Welcome back!')
      goNext()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Invalid MFA code'
      toast.error(typeof msg === 'string' ? msg : 'Invalid MFA code')
    } finally {
      setLoading(false)
    }
  }

  const resendVerification = async () => {
    const email = getValues('email')
    if (!email) {
      toast.error('Enter your email first')
      return
    }
    setResending(true)
    try {
      await api.post('/auth/resend-verification', { email })
      toast.success('If an unverified account exists, a verification email has been sent')
    } catch {
      toast.error('Could not resend verification email')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="inline-flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold text-xl">
              R
            </div>
            <span className="text-white font-bold text-2xl">RAGInspector</span>
          </Link>
          <h1 className="text-3xl font-bold text-white mb-3">{mfaToken ? 'Two-factor authentication' : 'Welcome back'}</h1>
          <p className="text-slate-400">
            {mfaToken ? (
              'Enter the code from your authenticator app (or a recovery code).'
            ) : (
              <>
                Don&apos;t have an account?{' '}
                <Link href="/auth/register" className="text-blue-400 hover:text-blue-300 font-medium">Sign up</Link>
              </>
            )}
          </p>
        </div>

        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-3xl p-8">
          {mfaToken ? (
            <form onSubmit={onMfaSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Authentication code</label>
                <input
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-400">
                <input
                  type="checkbox"
                  checked={rememberDevice}
                  onChange={(e) => setRememberDevice(e.target.checked)}
                  className="rounded border-slate-600"
                />
                Trust this device for 1 year
              </label>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 text-white py-3.5 rounded-xl font-semibold transition-all"
              >
                {loading ? 'Verifying…' : 'Verify and sign in'}
              </button>
              <button
                type="button"
                onClick={() => { setMfaToken(null); setMfaCode('') }}
                className="w-full text-sm text-slate-400 hover:text-slate-300"
              >
                Back to password
              </button>
            </form>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email address</label>
                <input
                  {...register('email')}
                  type="email"
                  placeholder="you@company.com"
                  className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
                {errors.email && <p className="text-red-400 text-xs mt-1.5">{errors.email.message}</p>}
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-slate-300">Password</label>
                  <Link href="/auth/forgot-password" className="text-xs text-blue-400 hover:text-blue-300 font-medium">
                    Forgot password?
                  </Link>
                </div>
                <input
                  {...register('password')}
                  type="password"
                  placeholder="••••••••"
                  className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
                {errors.password && <p className="text-red-400 text-xs mt-1.5">{errors.password.message}</p>}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 text-white py-3.5 rounded-xl font-semibold transition-all"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-700/60" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-slate-900/50 px-2 text-slate-500">or</span>
                </div>
              </div>
              <button
                type="button"
                disabled={loading}
                onClick={async () => {
                  setLoading(true)
                  try {
                    const { data } = await api.post('/identity/sso/google/authorize')
                    if (data?.authorization_url && data.status === 'ready') {
                      window.location.href = data.authorization_url
                      return
                    }
                    toast.error(data?.hint || 'Google SSO is not configured')
                  } catch {
                    toast.error('Could not start Google sign-in')
                  } finally {
                    setLoading(false)
                  }
                }}
                className="w-full border border-slate-700/60 hover:border-slate-600 text-slate-200 py-3.5 rounded-xl font-semibold transition-all disabled:opacity-50"
              >
                Continue with Google
              </button>
              {needsVerification && (
                <button
                  type="button"
                  disabled={resending}
                  onClick={resendVerification}
                  className="w-full text-sm text-blue-400 hover:text-blue-300 disabled:opacity-50"
                >
                  {resending ? 'Sending…' : 'Resend verification email'}
                </button>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
