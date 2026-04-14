import React, { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getDominance, getHeatmap } from '../api/cryptoApi'
import type { MarketDominance, MarketHeatmap } from '../api/types'

type LoadState<T> =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'loaded'; data: T; updatedAt: Date }
  | { kind: 'error'; message: string }

export const PulsePage: React.FC = () => {
  const { token } = useAuth()
  const [domState, setDomState] = useState<LoadState<MarketDominance>>({ kind: 'idle' })
  const [heatState, setHeatState] = useState<LoadState<MarketHeatmap>>({ kind: 'idle' })

  const load = async () => {
    if (!token) return
    setDomState({ kind: 'loading' })
    setHeatState({ kind: 'loading' })
    try {
      const [dom, heat] = await Promise.all([getDominance(token), getHeatmap(token, 7)])
      setDomState({ kind: 'loaded', data: dom.data, updatedAt: new Date() })
      setHeatState({ kind: 'loaded', data: heat.data, updatedAt: new Date() })
    } catch (e: any) {
      const msg = e?.message ?? 'Failed to load market pulse'
      setDomState({ kind: 'error', message: msg })
      setHeatState({ kind: 'error', message: msg })
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

  const heatTiles = useMemo(() => {
    if (heatState.kind !== 'loaded') return []
    return heatState.data.coins.map((c, i) => ({
      coin: c,
      change: heatState.data.change_pct_7d?.[i] ?? 0,
    }))
  }, [heatState])

  return (
    <>
      <div className="sectionHeader">
        <div>
          <div className="sectionKicker">Market pulse</div>
          <h2 className="sectionTitle">Dominance & heat</h2>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="pill">
            Updated: {domState.kind === 'loaded' ? domState.updatedAt.toLocaleTimeString() : '—'}
          </span>
          <button className="navBtn" type="button" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      <div className="grid">
        <section className="card" style={{ gridColumn: 'span 6' }}>
          <div className="sectionKicker">Market dominance</div>
          {domState.kind === 'loaded' ? (
            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
              {domState.data.labels.map((label, idx) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ fontWeight: 700 }}>{label.toUpperCase()}</div>
                  <div className="muted">
                    {(domState.data.dominance_pct?.[idx] ?? 0).toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
          ) : domState.kind === 'error' ? (
            <div className="neg">{domState.message}</div>
          ) : (
            <div className="muted">Loading dominance…</div>
          )}
        </section>

        <section className="card" style={{ gridColumn: 'span 6' }}>
          <div className="sectionKicker">7-day heat</div>
          {heatState.kind === 'loaded' ? (
            <div
              style={{
                marginTop: 10,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                gap: 10,
              }}
            >
              {heatTiles.map((t) => {
                const positive = t.change >= 0
                return (
                  <div
                    key={t.coin}
                    style={{
                      border: '1px solid var(--rule)',
                      borderRadius: 14,
                      padding: 12,
                      background: positive ? 'rgba(15,118,110,0.10)' : 'rgba(185,28,28,0.10)',
                    }}
                  >
                    <div style={{ fontWeight: 800 }}>{t.coin.toUpperCase()}</div>
                    <div className={positive ? 'pos' : 'neg'} style={{ marginTop: 6, fontWeight: 700 }}>
                      {positive ? '+' : ''}
                      {t.change.toFixed(2)}%
                    </div>
                  </div>
                )
              })}
            </div>
          ) : heatState.kind === 'error' ? (
            <div className="neg">{heatState.message}</div>
          ) : (
            <div className="muted">Loading heatmap…</div>
          )}
        </section>
      </div>
    </>
  )
}

