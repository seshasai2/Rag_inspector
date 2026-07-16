import api from '@/lib/api'
import { authCookieOptions } from '@/lib/cookies'
import Cookies from 'js-cookie'
import { create } from 'zustand'

interface User {
  id: string
  email: string
  name: string
  role: string
  subscription_plan: string
  subscription_status: string | null
  traces_this_month: number
  onboarding_completed: boolean
  email_verified: boolean
}

export type LoginResult =
  | { mfaRequired: false }
  | { mfaRequired: true; mfaToken: string }

interface AuthState {
  user: User | null
  loading: boolean
  setUser: (user: User | null) => void
  login: (email: string, password: string) => Promise<LoginResult>
  completeMfaLogin: (mfaToken: string, code: string, rememberDevice?: boolean) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
}

async function applyTokens(data: {
  access_token?: string | null
  refresh_token?: string | null
  device_token?: string | null
}) {
  if (!data.access_token || !data.refresh_token) {
    throw new Error('Login did not return session tokens')
  }
  Cookies.set('access_token', data.access_token, authCookieOptions(1 / 96))
  Cookies.set('refresh_token', data.refresh_token, authCookieOptions(7))
  if (data.device_token) {
    Cookies.set('mfa_device_token', data.device_token, authCookieOptions(365))
  }
}

function clearSession() {
  const opts = { path: '/' }
  Cookies.remove('access_token', opts)
  Cookies.remove('refresh_token', opts)
  Cookies.remove('mfa_device_token', opts)
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,

  setUser: (user) => set({ user }),

  login: async (email, password) => {
    const deviceToken = Cookies.get('mfa_device_token')
    const { data } = await api.post('/auth/login', {
      email,
      password,
      device_token: deviceToken || undefined,
    })
    if (data.mfa_required) {
      return { mfaRequired: true, mfaToken: data.mfa_token as string }
    }
    await applyTokens(data)
    const me = await api.get('/auth/me')
    set({ user: me.data, loading: false })
    return { mfaRequired: false }
  },

  completeMfaLogin: async (mfaToken, code, rememberDevice = false) => {
    const { data } = await api.post('/auth/login/mfa', {
      mfa_token: mfaToken,
      code,
      remember_device: rememberDevice,
    })
    await applyTokens(data)
    const me = await api.get('/auth/me')
    set({ user: me.data, loading: false })
  },

  logout: async () => {
    const refreshToken = Cookies.get('refresh_token')
    const accessToken = Cookies.get('access_token')
    try {
      if (refreshToken) {
        await api.post('/auth/logout', {
          refresh_token: refreshToken,
          access_token: accessToken || undefined,
        })
      }
    } catch {
      /* best-effort */
    }
    clearSession()
    set({ user: null, loading: false })
  },

  fetchMe: async () => {
    const token = Cookies.get('access_token')
    if (!token) {
      set({ loading: false })
      return
    }
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },
}))
