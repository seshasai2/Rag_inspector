/** Cookie option helpers for auth tokens (js-cookie — not HttpOnly by design). */
export type CookieSameSite = 'strict' | 'lax' | 'none'

export function authCookieOptions(expiresDays: number): {
  expires: number
  path: string
  sameSite: CookieSameSite
  secure: boolean
} {
  const isBrowser = typeof window !== 'undefined'
  const isHttps = isBrowser && window.location.protocol === 'https:'
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''
  const apiIsHttps = apiUrl.startsWith('https://')
  return {
    expires: expiresDays,
    path: '/',
    sameSite: 'lax',
    secure: isHttps || apiIsHttps,
  }
}

export function clearAuthCookies(): void {
  // Imported lazily in callers that already use js-cookie.
}
