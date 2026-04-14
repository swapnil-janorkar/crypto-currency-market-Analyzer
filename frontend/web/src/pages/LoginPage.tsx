import React, { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = useMemo(() => (location.state as { from?: string } | null)?.from ?? '/', [location])

  const [username, setUsername] = useState('demo')
  const [password, setPassword] = useState('demo123')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login({ username, password })
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err?.message ?? 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container">
      <div className="masthead">
        <div className="mastheadTop">
          <div className="brand">
            <div className="brandTitle">CryptoSight</div>
            <div className="brandTag">SignIn</div>
          </div>
        </div>
        <div className="contentGrid">
          <div className="sectionHeader">
            <div>
              <div className="sectionKicker">Authentication</div>
              <h1 className="sectionTitle" style={{ fontSize: 26, margin: 0 }}>
                Welcome back.
              </h1>
            </div>
            <span className="pill">Demo: demo / demo123</span>
          </div>
          <div className="card" style={{ maxWidth: 520 }}>
            <form onSubmit={onSubmit} style={{ display: 'grid', gap: 10 }}>
              <label style={{ display: 'grid', gap: 6 }}>
                <span className="muted" style={{ fontSize: 12, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                  Username
                </span>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  style={{ padding: 10, borderRadius: 12, border: '1px solid var(--rule)', background: 'transparent', color: 'var(--ink)' }}
                />
              </label>
              <label style={{ display: 'grid', gap: 6 }}>
                <span className="muted" style={{ fontSize: 12, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                  Password
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ padding: 10, borderRadius: 12, border: '1px solid var(--rule)', background: 'transparent', color: 'var(--ink)' }}
                />
              </label>
              {error ? <div className="neg" style={{ fontSize: 13 }}>{error}</div> : null}
              <button className="navBtn" type="submit" disabled={busy} style={{ justifySelf: 'start' }}>
                {busy ? 'Signing in…' : 'Sign in'}
              </button>
              <div className="muted" style={{ fontSize: 12 }}>
                Note: most dashboard endpoints require a bearer token now.
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

