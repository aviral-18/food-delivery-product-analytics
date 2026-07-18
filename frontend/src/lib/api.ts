import axios, { type AxiosInstance } from 'axios'

const TOKEN_KEY = 'eternal_access_token'
const REFRESH_KEY = 'eternal_refresh_token'

export const tokenStore = {
  get access() {
    return localStorage.getItem(TOKEN_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh
  if (!refresh) return null
  try {
    const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
    tokenStore.set(res.data.access_token, res.data.refresh_token)
    return res.data.access_token
  } catch {
    tokenStore.clear()
    return null
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      refreshing = refreshing ?? tryRefresh()
      const token = await refreshing
      refreshing = null
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      // hard logout on refresh failure
      tokenStore.clear()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

/** Build a query string from the global filters, dropping empty values. */
export function toQuery(params: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0)) continue
    out[k] = v
  }
  return out
}
