import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Cookie presence gate for authenticated app routes.
 * Full session validation happens client-side via /auth/me in the app layout.
 */
export function middleware(request: NextRequest) {
  const access = request.cookies.get('access_token')?.value
  const refresh = request.cookies.get('refresh_token')?.value

  if (!access && !refresh) {
    const loginUrl = new URL('/auth/login', request.url)
    loginUrl.searchParams.set('next', request.nextUrl.pathname + request.nextUrl.search)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/queries/:path*',
    '/chunks/:path*',
    '/knowledge/:path*',
    '/autofix/:path*',
    '/documents/:path*',
    '/monitoring/:path*',
    '/regression/:path*',
    '/benchmark/:path*',
    '/studio/:path*',
    '/investigator/:path*',
    '/executive/:path*',
    '/team/:path*',
    '/metrics/:path*',
    '/pipelines/:path*',
    '/settings/:path*',
    '/admin/:path*',
    '/enterprise/:path*',
  ],
}
