'use client'

import { Position } from '@/lib/api-client'
import {
  formatCurrency,
  formatNumber,
  getPnLColor,
  getPnLBgColor,
  cn,
} from '@/lib/utils'
import { useState } from 'react'

interface PositionsGridProps {
  positions?: Position[]
  loading?: boolean
  onClosePosition?: (ticker: string) => Promise<void>
}

export function PositionsGrid({
  positions,
  loading,
  onClosePosition,
}: PositionsGridProps) {
  const [closingTicker, setClosingTicker] = useState<string | null>(null)

  const handleClose = async (ticker: string) => {
    if (!onClosePosition) return
    setClosingTicker(ticker)
    try {
      await onClosePosition(ticker)
    } finally {
      setClosingTicker(null)
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-md">
        <div className="h-32 bg-surface-card rounded-lg"></div>
        <div className="h-32 bg-surface-card rounded-lg"></div>
      </div>
    )
  }

  if (!positions || positions.length === 0) {
    return (
      <div className="card text-center py-lg">
        <p className="text-body-md text-muted">No open positions</p>
      </div>
    )
  }

  return (
    <div className="space-y-md">
      <h3 className="text-title-lg font-semibold">Open Positions</h3>
      <div className="grid grid-cols-1 gap-md">
        {positions.map((position) => (
          <div key={position.ticker} className="card flex justify-between items-start">
            <div className="flex-1">
              {/* Ticker & Market Name */}
              <div className="mb-md">
                <h4 className="text-title-md font-semibold text-on-dark">
                  {position.ticker}
                </h4>
                <p className="text-caption text-muted">{position.market_name}</p>
              </div>

              {/* Side Badge */}
              <div className="mb-md">
                <span
                  className={cn(
                    'badge text-caption font-semibold',
                    position.side === 'YES'
                      ? 'bg-trading-up/20 text-trading-up'
                      : 'bg-trading-down/20 text-trading-down'
                  )}
                >
                  {position.side} • {position.quantity} contract
                  {position.quantity !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Pricing Info */}
              <div className="grid grid-cols-2 gap-md text-caption">
                <div>
                  <p className="text-muted mb-xs">Entry Price</p>
                  <p className="text-number-sm font-mono text-body">
                    {formatCurrency(position.entry_price)}
                  </p>
                </div>
                <div>
                  <p className="text-muted mb-xs">Current Price</p>
                  <p className="text-number-sm font-mono text-body">
                    {formatCurrency(position.current_price)}
                  </p>
                </div>
                <div>
                  <p className="text-muted mb-xs">Exposure</p>
                  <p className="text-number-sm font-mono text-body">
                    {formatCurrency(position.exposure)}
                  </p>
                </div>
                <div>
                  <p className="text-muted mb-xs">Realized P&L</p>
                  <p className={`text-number-sm font-mono ${getPnLColor(position.realized_pnl)}`}>
                    {position.realized_pnl >= 0 ? '+' : ''}
                    {formatCurrency(position.realized_pnl)}
                  </p>
                </div>
              </div>

              {/* Edge & Confidence */}
              <div className="grid grid-cols-2 gap-md mt-md text-caption">
                <div>
                  <p className="text-muted mb-xs">Edge</p>
                  <p className="text-number-sm font-mono text-primary">
                    {position.edge_pct.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-muted mb-xs">Confidence</p>
                  <p className="text-number-sm font-mono text-body">
                    {position.confidence}/100
                  </p>
                </div>
              </div>
            </div>

            {/* Close Button */}
            <div className="ml-lg">
              <button
                onClick={() => handleClose(position.ticker)}
                disabled={closingTicker === position.ticker}
                className="btn-primary whitespace-nowrap"
              >
                {closingTicker === position.ticker ? '⏳ Closing...' : '✕ Close'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
