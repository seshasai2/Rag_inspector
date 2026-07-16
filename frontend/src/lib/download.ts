import Cookies from 'js-cookie'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Download a file from the FastAPI backend with the current Bearer token.
 * Plain <a href="/api/v1/..."> hits Next.js, not the API, and omits auth.
 */
export async function downloadAuthenticatedFile(
  path: string,
  filename: string,
  params?: Record<string, string>,
): Promise<void> {
  const token = Cookies.get('access_token')
  const search = params ? `?${new URLSearchParams(params).toString()}` : ''
  const url = path.startsWith('http')
    ? `${path}${search}`
    : `${API_URL}/api/v1${path.startsWith('/') ? path : `/${path}`}${search}`

  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    let detail = `Download failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail)
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const data = await response.json()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    triggerBlobDownload(blob, filename.endsWith('.json') ? filename : `${filename}.json`)
    return
  }

  const blob = await response.blob()
  triggerBlobDownload(blob, filename)
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}
