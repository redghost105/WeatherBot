'use client'

import { Signal } from '@/lib/api-client'
import {
  formatTimestamp,
  getSignalColor,
  getSignalBgColor,
  getStatusColor,
} from '@/lib/utils'

interface SignalsFeedProps {
  signals?: Signal[]
  loading?: boolean
}

export function SignalsFeed({ signals, loading }: SignalsFeedProps) {
  if (loading) {
    return (
      <div className="animate-pulse space-y-md">
        <div className="h-20 bg-surface-card rounded-lg"></div>
        <div className="h-20 bg-surface-card rounded-lg"></div>
      </div>
    )
  }

  if (!signals || signals.length === 0) {
    return (
      <div className="card text-center py-lg">
        <p className="text-body-md text-muted">No signals yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-md">
      <h3 className="text-title-lg font-semibold">Active Signals (Last 1h)</h3>
      <div className="space-y-sm max-h-96 overflow-y-auto">
        {signals.slice(0, 20).map((signal, idx) => (
          <div
            key={idx}
            className={`card p-md ${getSignalBgColor(signal.recommendation)}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                {/* Time & Ticker */}
                <div className="mb-xs">
                  <p className="text-caption text-muted">
                    {formatTimestamp(signal.timestamp)}
                  </p>
                  <h4 className="text-title-sm font-semibold text-on-dark">
                    {signal.ticker}
                  </h4>
                </div>

                {/* Recommendation Badge */}
                <div className="mb-sm">
                  <span
                    className={`badge text-caption font-semibold ${getSignalColor(signal.recommendation)}`}
                  >
                    {signal.recommendation}
                  </span>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-md text-caption">
                  <div>
                    <p className="text-muted">Edge</p>
                    <p className="text-number-sm font-mono text-primary">
                      {signal.edge_pct.toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-muted">Confidence</p>
                    <p className="text-number-sm font-mono text-body">
                      {signal.confidence}/100
                    </p>
                  </div>
                </div>

                {/* Reason */}
                {signal.reason && (
                  <p className="text-caption text-muted mt-sm">{signal.reason}</p>
                )}
              </div>

              {/* Status Badge */}
              <div className="ml-md">
                <span className={`badge text-caption font-semibold ${getStatusColor(signal.status)}`}>
                  {signal.status === 'executed' && '✓'}
                  {signal.status === 'rejected' && '✗'}
                  {signal.status === 'pending' && '⏳'}
                  {' '}
                  {signal.status}
                </span>
                {signal.execution_count && (
                  <p className="text-caption text-muted mt-xs">
                    {signal.execution_count} order{signal.execution_count !== 1 ? 's' : ''}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
