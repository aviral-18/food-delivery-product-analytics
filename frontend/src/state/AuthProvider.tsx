import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokenStore } from '@/lib/api'
import type { User } from '@/types'

interface AuthCtx {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function bootstrap() {
      if (!tokenStore.access) {
        setLoading(false)
        return
      }
      try {
        const res = await api.get<User>('/auth/me')
        if (active) setUser(res.data)
      } catch {
        tokenStore.clear()
      } finally {
        if (active) setLoading(false)
      }
    }
    bootstrap()
    return () => {
      active = false
    }
  }, [])

  async function login(email: string, password: string) {
    const res = await api.post('/auth/login', { email, password })
    tokenStore.set(res.data.access_token, res.data.refresh_token)
    const me = await api.get<User>('/auth/me')
    setUser(me.data)
  }

  function logout() {
    tokenStore.clear()
    setUser(null)
    window.location.href = '/login'
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(Ctx)
