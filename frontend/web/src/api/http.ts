export type ApiError = {
  status: number
  message: string
  detail?: unknown
}

export const getApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined
  if (envBase?.trim()) return envBase.replace(/\/+$/, '')

  // Default: same host when served by FastAPI; during `vite dev` use 8000.
  if (window.location.port === '5173') return 'http://127.0.0.1:8000'
  return `${window.location.protocol}//${window.location.host}`
}

export async function apiFetch<T>(
  path: string,
  opts: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const base = getApiBase()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  const headers = new Headers(opts.headers)
  headers.set('Accept', 'application/json')
  if (opts.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (opts.token) {
    headers.set('Authorization', `Bearer ${opts.token}`)
  }

  const res = await fetch(url, { ...opts, headers })
  const contentType = res.headers.get('content-type') || ''

  if (!res.ok) {
    let message = `Request failed (${res.status})`
    let detail: unknown = undefined
    try {
      if (contentType.includes('application/json')) {
        const data = await res.json()
        detail = data
        message = (data?.detail as string) || message
      } else {
        const text = await res.text()
        if (text) message = text
      }
    } catch {
      // ignore parse errors
    }
    const err: ApiError = { status: res.status, message, detail }
    throw err
  }

  if (contentType.includes('application/json')) {
    return (await res.json()) as T
  }

  // Shouldn't happen for this API, but keeps typing sound.
  return (await res.text()) as unknown as T
}

