const TOKEN_KEY = 'mindmap_access_token'
const REFRESH_KEY = 'mindmap_refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (isRefreshing && refreshPromise) return refreshPromise

  isRefreshing = true
  refreshPromise = (async () => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) return false

    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) return false
      const data = await res.json()
      setTokens(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function api(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken()
  const headers = new Headers(options.headers || {})
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json')
  }

  let res = await fetch(url, { ...options, headers })

  // If 401, try refresh and retry once
  if (res.status === 401 && getRefreshToken()) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      const newToken = getAccessToken()
      headers.set('Authorization', `Bearer ${newToken}`)
      res = await fetch(url, { ...options, headers })
    }
  }

  return res
}

export async function apiJson<T = any>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await api(url, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}
