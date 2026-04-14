import React, { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getLiveData } from '../api/cryptoApi'
import type { LiveCoinRow } from '../api/types'
import { formatCompact, formatCurrency } from '../components/Format'

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'loaded'; rows: LiveCoinRow[]; updatedAt: Date }
  | { kind: 'error'; message: string }

export const OverviewPage: React.FC = () => {
  const { token } = useAuth()
  const [state, setState] = useState<LoadState>({ kind: 'idle' })

  const load = async () => {
    if (!token) return
    setState({ kind: 'loading' })
    try {
      const res = await getLiveData(token)
      setState({ kind: 'loaded', rows: res.data ?? [], updatedAt: new Date() })
    } catch (e: any) {
      setState({ kind: 'error', message: e?.message ?? 'Failed to load live data' })
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!token) return
    const id = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const top = useMemo(() => {
    if (state.kind !== 'loaded') return []
    return [...state.rows].sort((a, b) => (b.market_cap ?? 0) - (a.market_cap ?? 0)).slice(0, 6)
  }, [state])

  return (
    <>
      <div className="sectionHeader">
        <div>
          <div className="sectionKicker">Live snapshot</div>
          <h2 className="sectionTitle">Market breadth</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span className="pill">
            Refresh: {state.kind === 'loaded' ? state.updatedAt.toLocaleTimeString() : '—'}
          </span>
          <button className="navBtn" type="button" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      {state.kind === 'error' ? (
        <div className="card neg">{state.message}</div>
      ) : null}

      {state.kind === 'loading' || state.kind === 'idle' ? (
        <div className="card">Loading live data…</div>
      ) : null}

      {state.kind === 'loaded' ? (
        <div className="grid">
          {top.map((row) => {
            const change = row.change_percentage_24h ?? 0
            const changeClass = change >= 0 ? 'pos' : 'neg'
            return (
              <article
                key={row.coin}
                className="card"
                style={{ gridColumn: 'span 4', cursor: 'default' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ fontFamily: `'Libre Baskerville', Georgia, serif`, fontWeight: 700 }}>
                    {row.coin.toUpperCase()}
                  </div>
                  <div className={changeClass} style={{ fontWeight: 600 }}>
                    {change >= 0 ? '+' : ''}
                    {change.toFixed(2)}%
                  </div>
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 10 }}>{formatCurrency(row.price)}</div>
                <div className="muted" style={{ fontSize: 13, marginTop: 8 }}>
                  Volume · {formatCompact(row.volume)} · MktCap · {formatCompact(row.market_cap)}
                </div>
              </article>
            )
          })}
          <div className="card" style={{ gridColumn: 'span 12' }}>
            <div className="sectionKicker">Editor’s note</div>
            <div style={{ marginTop: 8, color: 'var(--ink-2)' }}>
              If any tiles remain empty, ensure your pipeline is running and that you’re logged in
              (demo user is seeded automatically).
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

