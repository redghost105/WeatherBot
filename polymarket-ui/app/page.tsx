'use client'

import { useEffect, useState } from 'react'
import { HeroBand } from '@/components/HeroBand'
import { PositionsGrid } from '@/components/PositionsGrid'
import { SignalsFeed } from '@/components/SignalsFeed'
import { EquityCurve } from '@/components/EquityCurve'
import { SystemStatus } from '@/components/SystemStatus'
import { PolymarketAPI, Portfolio, Position, Signal, PerformanceData, HealthStatus, ClosePositionResponse } from '@/lib/api-client'

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [performance, setPerformance] = useState<PerformanceData | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [closedTickers, setClosedTickers] = useState<Set<string>>(new Set())

  // Fetch all data
  const fetchData = async () => {
    try {
      setError(null)
      const [portfolioData, positionsData, signalsData, performanceData, healthData] = await Promise.all([
        PolymarketAPI.getPortfolio(),
        PolymarketAPI.getPositions(),
        PolymarketAPI.getSignals(),
        PolymarketAPI.getPerformance(),
        PolymarketAPI.getHealth(),
      ])

      setPortfolio(portfolioData)
      setPositions(positionsData.filter((p) => !closedTickers.has(p.ticker)))
      setSignals(signalsData)
      setPerformance(performanceData)
      setHealth(healthData)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
      setLoading(false)
    }
  }

  // Initial fetch
  useEffect(() => {
    fetchData()
  }, [])

  // Poll every 5 seconds
  useEffect(() => {
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [closedTickers])

  // Handle close position
  const handleClosePosition = async (ticker: string) => {
    try {
      await PolymarketAPI.closePosition(ticker)
      setClosedTickers((prev) => new Set([...prev, ticker]))
      // Fetch updated positions
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close position')
    }
  }

  return (
    <div className="min-h-screen bg-canvas p-lg">
      {/* Error banner */}
      {error && (
        <div className="mb-lg p-md bg-trading-down/20 border border-trading-down rounded-lg">
          <p className="text-trading-down text-body-md">⚠️ {error}</p>
        </div>
      )}

      {/* Hero band with main metrics */}
      <HeroBand data={portfolio} loading={loading} />

      {/* Two-column layout: Positions + Signals */}
      <div className="grid grid-cols-2 gap-lg mb-lg">
        <PositionsGrid
          positions={positions}
          loading={loading}
          onClosePosition={handleClosePosition}
        />
        <SignalsFeed signals={signals} loading={loading} />
      </div>

      {/* Charts row */}
      <div className="mb-lg">
        <EquityCurve data={performance} loading={loading} />
      </div>

      {/* System status */}
      <SystemStatus health={health} loading={loading} />
    </div>
  )
}
