/**
 * API Client for Polymarket Trading Engine
 * Handles all communication with backend routes
 */

const API_BASE = '/api'

export interface Portfolio {
  equity: number
  dailyPnL: number
  dailyPnLPct: number
  winRate: number
  positions_count: number
  trades_today: number
  engine_status: string
  engine_uptime_seconds: number
  restart_count: number
  last_scan: string
}

export interface Position {
  ticker: string
  side: 'YES' | 'NO'
  quantity: number
  entry_price: number
  current_price: number
  exposure: number
  realized_pnl: number
  edge_pct: number
  confidence: number
  market_name: string
}

export interface Signal {
  timestamp: string
  ticker: string
  edge_pct: number
  confidence: number
  recommendation: 'STRONG_BUY' | 'BUY' | 'SKIP' | 'SELL_NO'
  status: 'executed' | 'rejected' | 'pending'
  execution_count?: number
  reason?: string
}

export interface PerformanceData {
  timeline: Array<{ timestamp: string; equity: number }>
  daily_bars: Array<{ date: string; pnl: number; trades: number }>
}

export interface HealthStatus {
  engine_running: boolean
  uptime_seconds: number
  restarts: number
  last_signal: string
  last_execution: string
  signals_per_minute: number
  validation_rate: number
  error_count: number
  log_file: string
}

export interface ClosePositionResponse {
  success: boolean
  ticker: string
  side: string
  quantity: number
  executed_price: number
  order_id: string
}

export class PolymarketAPI {
  static async getPortfolio(): Promise<Portfolio> {
    const res = await fetch(`${API_BASE}/portfolio`)
    if (!res.ok) throw new Error(`Failed to fetch portfolio: ${res.statusText}`)
    return res.json()
  }

  static async getPositions(): Promise<Position[]> {
    const res = await fetch(`${API_BASE}/positions`)
    if (!res.ok) throw new Error(`Failed to fetch positions: ${res.statusText}`)
    return res.json()
  }

  static async getSignals(): Promise<Signal[]> {
    const res = await fetch(`${API_BASE}/signals`)
    if (!res.ok) throw new Error(`Failed to fetch signals: ${res.statusText}`)
    return res.json()
  }

  static async getPerformance(): Promise<PerformanceData> {
    const res = await fetch(`${API_BASE}/performance`)
    if (!res.ok) throw new Error(`Failed to fetch performance: ${res.statusText}`)
    return res.json()
  }

  static async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`)
    if (!res.ok) throw new Error(`Failed to fetch health: ${res.statusText}`)
    return res.json()
  }

  static async closePosition(ticker: string): Promise<ClosePositionResponse> {
    const res = await fetch(`${API_BASE}/close/${ticker}`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to close position: ${res.statusText}`)
    return res.json()
  }

  static async fetchAll() {
    return Promise.all([
      this.getPortfolio(),
      this.getPositions(),
      this.getSignals(),
      this.getPerformance(),
      this.getHealth(),
    ]).then(([portfolio, positions, signals, performance, health]) => ({
      portfolio,
      positions,
      signals,
      performance,
      health,
    }))
  }
}
