'use client'
import api from '@/lib/api'
import { CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(token ? 'loading' : 'error')
  const [message, setMessage] = useState(token ? 'Verifying your email...' : 'Verification link is missing a token.')

  useEffect(() => {
    if (!token) return

    api.get('/auth/verify-email', { params: { token } })
      .then((res) => {
        setStatus('success')
        setMessage(res.data.message || 'Email verified successfully.')
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err?.response?.data?.detail || 'Verification link is invalid or expired.')
      })
  }, [token])

  const isSuccess = status === 'success'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="inline-flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold text-xl">R</div>
            <span className="text-white font-bold text-2xl">RAGInspector</span>
          </Link>
          <h1 className="text-3xl font-bold text-white mb-3">Email verification</h1>
          <p className="text-slate-400">{message}</p>
        </div>

        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-3xl p-8 text-center">
          <div className={`w-16 h-16 rounded-2xl border flex items-center justify-center mx-auto mb-5 ${
            isSuccess ? 'bg-green-500/10 border-green-500/20' : status === 'loading' ? 'bg-blue-500/10 border-blue-500/20' : 'bg-red-500/10 border-red-500/20'
          }`}>
            {status === 'loading' ? (
              <div className="w-6 h-6 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
            ) : isSuccess ? (
              <CheckCircle size={28} className="text-green-400" />
            ) : (
              <XCircle size={28} className="text-red-400" />
            )}
          </div>
          <Link href={isSuccess ? '/dashboard' : '/auth/login'} className="inline-block w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white py-3.5 rounded-xl font-semibold transition-all">
            {isSuccess ? 'Go to dashboard' : 'Back to sign in'}
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <VerifyEmailContent />
    </Suspense>
  )
}
