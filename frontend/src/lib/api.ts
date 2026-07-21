import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import Cookies from 'js-cookie'
import { authCookieOptions } from '@/lib/cookies'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Render Free cold starts often return 502 briefly — retry a few times. */
const COLD_START_STATUSES = new Set([502, 503, 504])
const MAX_COLD_RETRIES = 4
const COLD_RETRY_DELAY_MS = 2500

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  // Free-tier wake + first query can exceed 30s
  timeout: 60_000,
})

api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  failedQueue = []
}

function clearSessionCookies() {
  const opts = { path: '/' }
  Cookies.remove('access_token', opts)
  Cookies.remove('refresh_token', opts)
  Cookies.remove('mfa_device_token', opts)
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isColdStartError(error: AxiosError): boolean {
  const status = error.response?.status
  if (status && COLD_START_STATUSES.has(status)) return true
  // No response = network / connection reset while Render is waking
  if (!error.response && (error.code === 'ERR_NETWORK' || error.message === 'Network Error')) {
    return true
  }
  if (error.code === 'ECONNABORTED') return true
  return false
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
      _coldRetry?: number
    }
    if (!originalRequest) return Promise.reject(error)

    // Retry transient Render Free wake failures before treating as fatal
    if (isColdStartError(error)) {
      const attempt = originalRequest._coldRetry ?? 0
      if (attempt < MAX_COLD_RETRIES) {
        originalRequest._coldRetry = attempt + 1
        await sleep(COLD_RETRY_DELAY_MS * (attempt + 1))
        return api(originalRequest)
      }
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }
      originalRequest._retry = true
      isRefreshing = true
      const refreshToken = Cookies.get('refresh_token')
      if (!refreshToken) {
        isRefreshing = false
        clearSessionCookies()
        if (typeof window !== 'undefined') window.location.href = '/auth/login'
        return Promise.reject(error)
      }
      try {
        const { data } = await axios.post(
          `${API_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken },
          { timeout: 60_000 },
        )
        Cookies.set('access_token', data.access_token, authCookieOptions(1 / 96))
        Cookies.set('refresh_token', data.refresh_token, authCookieOptions(7))
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (err) {
        processQueue(err, null)
        clearSessionCookies()
        if (typeof window !== 'undefined') window.location.href = '/auth/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  },
)

export default api
export { getApiErrorMessage } from '@/lib/errors'
