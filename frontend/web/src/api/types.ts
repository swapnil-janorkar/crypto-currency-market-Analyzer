export type LiveCoinRow = {
  coin: string
  timestamp: string
  price: number
  volume?: number
  market_cap?: number
  circulating_supply?: number
  change_percentage_24h?: number
  change_percentage_7d?: number
}

export type LiveDataResponse = {
  status: 'success'
  count: number
  data: LiveCoinRow[]
}

export type Prediction = {
  coin: string
  model_name: string
  predicted_price: number
  current_price: number
  confidence: number
  trend: 'bullish' | 'bearish' | 'neutral'
  prediction_time: string
  target_time: string
}

export type PredictionResponse = {
  status: 'success'
  data: Prediction
}

export type InsightsResponse = {
  status: 'success'
  coin: string
  trend: 'bullish' | 'bearish' | 'neutral'
  current_price: number
  predicted_price: number
  insight: string
}

export type PriceChart = {
  labels: string[]
  price: number[]
  sma_7?: number[]
  sma_30?: number[]
  rsi?: number[]
  macd?: number[]
  predicted?: Array<number | null>
}

export type VisualizationsResponse = {
  status: 'success'
  price_chart: PriceChart
  volume_spikes: unknown
}

export type MarketDominance = {
  labels: string[]
  market_caps?: number[]
  dominance_pct?: number[]
}

export type MarketHeatmap = {
  coins: string[]
  change_pct_7d: number[]
  heatmap?: unknown
}

