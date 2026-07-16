import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import Cookies from 'js-cookie'
import { authCookieOptions } from '@/lib/cookies'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
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

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
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
          { timeout: 15_000 },
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
