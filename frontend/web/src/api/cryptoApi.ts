import { apiFetch } from './http'
import type {
  InsightsResponse,
  LiveDataResponse,
  MarketDominance,
  MarketHeatmap,
  PredictionResponse,
  VisualizationsResponse,
} from './types'

export const getLiveData = (token: string) => apiFetch<LiveDataResponse>('/live-data', { token })

export const getPrediction = (token: string, coin: string) =>
  apiFetch<PredictionResponse>(`/prediction/${coin}?model=xgboost`, { token })

export const getInsight = (token: string, coin: string) =>
  apiFetch<InsightsResponse>(`/insights/${coin}`, { token })

export const getVisualizations = (token: string, coin: string, days = 30) =>
  apiFetch<VisualizationsResponse>(`/visualizations/${coin}?days=${days}`, { token })

export const getDominance = (token: string) =>
  apiFetch<{ status: 'success'; data: MarketDominance }>(`/visualizations/market/dominance`, {
    token,
  })

export const getHeatmap = (token: string, days = 7) =>
  apiFetch<{ status: 'success'; data: MarketHeatmap }>(`/visualizations/market/heatmap?days=${days}`, {
    token,
  })

