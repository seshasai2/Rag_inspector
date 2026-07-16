'use client'
import api from '@/lib/api'
import Link from 'next/link'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, Mail } from 'lucide-react'

const schema = z.object({
  email: z.string().email('Invalid email'),
})

type FormData = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      await api.post('/auth/forgot-password', null, { params: { email: data.email } })
      setSent(true)
      toast.success('Reset email sent')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not send reset email'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="inline-flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold text-xl">R</div>
            <span className="text-white font-bold text-2xl">RAGInspector</span>
          </Link>
          <h1 className="text-3xl font-bold text-white mb-3">Reset your password</h1>
          <p className="text-slate-400">Enter your email and we will send a secure reset link.</p>
        </div>

        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-3xl p-8">
          {sent ? (
            <div className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-4">
                <Mail size={24} className="text-green-400" />
              </div>
              <p className="text-white font-semibold mb-2">Check your inbox</p>
              <p className="text-sm text-slate-400 mb-6">If an account exists for that email, a password reset link is on the way.</p>
              <Link href="/auth/login" className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm font-medium">
                <ArrowLeft size={16} />
                Back to sign in
              </Link>
            </div>
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

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 text-white py-3.5 rounded-xl font-semibold transition-all"
              >
                {loading ? 'Sending...' : 'Send reset link'}
              </button>

              <Link href="/auth/login" className="flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white">
                <ArrowLeft size={16} />
                Back to sign in
              </Link>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
