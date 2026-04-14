import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api/http'

type AuthState = {
  token: string | null
  username: string | null
  status: 'loading' | 'authenticated' | 'anonymous'
}

type LoginInput = {
  username: string
  password: string
}

type AuthContextValue = AuthState & {
  login: (input: LoginInput) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY = 'cryptosight_auth'

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [status, setStatus] = useState<AuthState['status']>('loading')

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        setStatus('anonymous')
        return
      }
      const parsed = JSON.parse(raw) as { token?: string; username?: string }
      if (parsed.token) setToken(parsed.token)
      if (parsed.username) setUsername(parsed.username)
      setStatus(parsed.token ? 'authenticated' : 'anonymous')
    } catch {
      setStatus('anonymous')
    }
  }, [])

  const persist = (nextToken: string | null, nextUsername: string | null) => {
    setToken(nextToken)
    setUsername(nextUsername)
    if (nextToken) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: nextToken, username: nextUsername }))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const login = async (input: LoginInput) => {
    const res = await apiFetch<{ access_token: string; token_type: string; username: string }>(
      '/auth/login',
      { method: 'POST', body: JSON.stringify(input) },
    )
    persist(res.access_token, res.username)
    setStatus('authenticated')
  }

  const logout = () => {
    persist(null, null)
    setStatus('anonymous')
  }

  // Validate token once on app load (best effort)
  useEffect(() => {
    const run = async () => {
      if (!token) return
      try {
        await apiFetch('/auth/me', { token })
      } catch {
        logout()
      }
    }
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const value = useMemo<AuthContextValue>(
    () => ({ token, username, status, login, logout }),
    [token, username, status],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

