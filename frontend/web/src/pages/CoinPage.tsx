import React, { useEffect, useMemo, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { useAuth } from '../auth/AuthContext'
import { getInsight, getLiveData, getPrediction, getVisualizations } from '../api/cryptoApi'
import { formatCurrency } from '../components/Format'
import type { PriceChart } from '../api/types'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

type LoadState<T> =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'loaded'; data: T; updatedAt: Date }
  | { kind: 'error'; message: string }

export const CoinPage: React.FC = () => {
  const { token } = useAuth()
  const [coin, setCoin] = useState<string>('bitcoin')

  const [coinsState, setCoinsState] = useState<LoadState<string[]>>({ kind: 'idle' })
  const [predState, setPredState] = useState<LoadState<any>>({ kind: 'idle' })
  const [insightState, setInsightState] = useState<LoadState<string>>({ kind: 'idle' })
  const [chartState, setChartState] = useState<LoadState<PriceChart>>({ kind: 'idle' })

  const loadCoins = async () => {
    if (!token) return
    setCoinsState({ kind: 'loading' })
    try {
      const res = await getLiveData(token)
      const coins = (res.data ?? []).map((r) => r.coin).filter(Boolean)
      setCoinsState({ kind: 'loaded', data: coins, updatedAt: new Date() })
      if (coins.length && !coins.includes(coin)) setCoin(coins[0])
    } catch (e: any) {
      setCoinsState({ kind: 'error', message: e?.message ?? 'Failed to load coins' })
    }
  }

  const loadCoin = async (c: string) => {
    if (!token) return
    setPredState({ kind: 'loading' })
    setInsightState({ kind: 'loading' })
    setChartState({ kind: 'loading' })
    try {
      const [pred, insight, viz] = await Promise.all([
        getPrediction(token, c),
        getInsight(token, c),
        getVisualizations(token, c, 30),
      ])
      setPredState({ kind: 'loaded', data: pred.data, updatedAt: new Date() })
      setInsightState({ kind: 'loaded', data: insight.insight, updatedAt: new Date() })
      setChartState({ kind: 'loaded', data: viz.price_chart, updatedAt: new Date() })
    } catch (e: any) {
      const msg = e?.message ?? 'Failed to load coin details'
      setPredState({ kind: 'error', message: msg })
      setInsightState({ kind: 'error', message: msg })
      setChartState({ kind: 'error', message: msg })
    }
  }

  useEffect(() => {
    void loadCoins()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!token) return
    void loadCoin(coin)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, coin])

  useEffect(() => {
    if (!token) return
    const id = window.setInterval(() => void loadCoin(coin), 60_000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, coin])

  const datasets = useMemo(() => {
    if (chartState.kind !== 'loaded') return null
    const p = chartState.data
    return {
      labels: p.labels,
      datasets: [
        {
          label: 'Price',
          data: p.price ?? [],
          borderColor: 'rgba(185,28,28,0.9)',
          backgroundColor: 'rgba(185,28,28,0.10)',
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.35,
        },
        ...(p.sma_7?.length
          ? [
              {
                label: 'SMA 7',
                data: p.sma_7,
                borderColor: 'rgba(15,118,110,0.9)',
                pointRadius: 0,
                borderWidth: 1.5,
                borderDash: [6, 6],
                tension: 0.3,
              },
            ]
          : []),
        ...(p.sma_30?.length
          ? [
              {
                label: 'SMA 30',
                data: p.sma_30,
                borderColor: 'rgba(96,86,79,0.9)',
                pointRadius: 0,
                borderWidth: 1.5,
                borderDash: [4, 8],
                tension: 0.3,
              },
            ]
          : []),
      ],
    }
  }, [chartState])

  return (
    <>
      <div className="sectionHeader">
        <div>
          <div className="sectionKicker">Coin focus</div>
          <h2 className="sectionTitle">{coin.toUpperCase()}</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <select
            value={coin}
            onChange={(e) => setCoin(e.target.value)}
            style={{
              padding: 10,
              borderRadius: 12,
              border: '1px solid var(--rule)',
              background: 'transparent',
              color: 'var(--ink)',
            }}
          >
            {coinsState.kind === 'loaded'
              ? coinsState.data.map((c) => (
                  <option key={c} value={c}>
                    {c.toUpperCase()}
                  </option>
                ))
              : null}
          </select>
          <button className="navBtn" type="button" onClick={() => void loadCoin(coin)}>
            Refresh
          </button>
        </div>
      </div>

      <div className="grid">
        <section className="card" style={{ gridColumn: 'span 5' }}>
          <div className="sectionKicker">Prediction</div>
          {predState.kind === 'loaded' ? (
            <>
              <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6 }}>
                {formatCurrency(predState.data.predicted_price)}
              </div>
              <div style={{ marginTop: 8 }}>
                <span className={predState.data.trend === 'bullish' ? 'pos' : predState.data.trend === 'bearish' ? 'neg' : 'muted'}>
                  {predState.data.trend.toUpperCase()}
                </span>{' '}
                <span className="muted">· XGBoost</span>
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 8 }}>
                Current · {formatCurrency(predState.data.current_price)} · Confidence ·{' '}
                {(predState.data.confidence * 100).toFixed(1)}%
              </div>
            </>
          ) : predState.kind === 'error' ? (
            <div className="neg">{predState.message}</div>
          ) : (
            <div className="muted">Loading prediction…</div>
          )}
        </section>

        <section className="card" style={{ gridColumn: 'span 7' }}>
          <div className="sectionKicker">Narrative</div>
          {insightState.kind === 'loaded' ? (
            <div style={{ marginTop: 8, lineHeight: 1.6, color: 'var(--ink-2)' }}>{insightState.data}</div>
          ) : insightState.kind === 'error' ? (
            <div className="neg">{insightState.message}</div>
          ) : (
            <div className="muted">Loading insight…</div>
          )}
        </section>

        <section className="card" style={{ gridColumn: 'span 12' }}>
          <div className="sectionHeader" style={{ margin: 0 }}>
            <div>
              <div className="sectionKicker">Chart</div>
              <h3 className="sectionTitle" style={{ margin: 0 }}>
                Price & moving averages (30d)
              </h3>
            </div>
            <span className="pill">
              Updated: {chartState.kind === 'loaded' ? chartState.updatedAt.toLocaleTimeString() : '—'}
            </span>
          </div>
          <div style={{ marginTop: 12, height: 360 }}>
            {datasets && chartState.kind === 'loaded' ? (
              <Line
                data={datasets}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { position: 'top' as const },
                    tooltip: { mode: 'index', intersect: false },
                  },
                  interaction: { mode: 'index', intersect: false },
                  scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: 'rgba(20,17,15,0.10)' } },
                  },
                }}
              />
            ) : chartState.kind === 'error' ? (
              <div className="neg">{chartState.message}</div>
            ) : (
              <div className="muted">Loading chart…</div>
            )}
          </div>
        </section>
      </div>
    </>
  )
}

