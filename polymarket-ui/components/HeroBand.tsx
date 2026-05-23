'use client'

import { Portfolio } from '@/lib/api-client'
import {
  formatCurrency,
  formatPercent,
  getPnLColor,
  formatTimestamp,
} from '@/lib/utils'

interface HeroBandProps {
  data?: Portfolio
  loading?: boolean
}

export function HeroBand({ data, loading }: HeroBandProps) {
  if (loading) {
    return (
      <div className="bg-surface-card rounded-xl p-lg mb-lg animate-pulse">
        <div className="h-12 bg-hairline rounded w-1/3"></div>
      </div>
    )
  }

  if (!data)
    return (
      <div className="bg-surface-card rounded-xl p-lg mb-lg text-muted">
        Loading portfolio data...
      </div>
    )

  return (
    <div className="bg-surface-card rounded-xl p-lg mb-lg border border-hairline">
      <div className="grid grid-cols-4 gap-lg">
        {/* Equity */}
        <div>
          <p className="text-caption text-muted mb-xs">Total Equity</p>
          <p className="text-number-display font-mono text-primary">
            {formatCurrency(data.equity)}
          </p>
        </div>

        {/* Daily P&L */}
        <div>
          <p className="text-caption text-muted mb-xs">Daily P&L</p>
          <div className="flex flex-col">
            <p
              className={`text-number-display font-mono ${getPnLColor(data.dailyPnL)}`}
            >
              {data.dailyPnL >= 0 ? '+' : ''}
              {formatCurrency(data.dailyPnL)}
            </p>
            <p className={`text-caption ${getPnLColor(data.dailyPnL)}`}>
              ({data.dailyPnLPct >= 0 ? '+' : ''}
              {formatPercent(data.dailyPnLPct / 100, 1)})
            </p>
          </div>
        </div>

        {/* Win Rate */}
        <div>
          <p className="text-caption text-muted mb-xs">Win Rate</p>
          <p className="text-number-display font-mono text-trading-up">
            {data.winRate.toFixed(0)}%
          </p>
          <p className="text-caption text-muted">
            {data.trades_today} trades today
          </p>
        </div>

        {/* Engine Status */}
        <div>
          <p className="text-caption text-muted mb-xs">Engine Status</p>
          <div className="flex items-center gap-sm mb-xs">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                data.engine_status === 'running'
                  ? 'bg-trading-up animate-pulse'
                  : 'bg-trading-down'
              }`}
            ></span>
            <p className="text-title-sm capitalize font-semibold">
              {data.engine_status}
            </p>
          </div>
          <p className="text-caption text-muted">
            Uptime: {Math.floor(data.engine_uptime_seconds / 60)}m · Last scan:{' '}
            {formatTimestamp(data.last_scan)}
          </p>
        </div>
      </div>
    </div>
  )
}
