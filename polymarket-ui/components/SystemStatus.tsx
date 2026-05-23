'use client'

import { HealthStatus } from '@/lib/api-client'
import { formatUptime, formatTimestamp } from '@/lib/utils'

interface SystemStatusProps {
  health?: HealthStatus
  loading?: boolean
}

export function SystemStatus({ health, loading }: SystemStatusProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-24 bg-hairline rounded"></div>
      </div>
    )
  }

  if (!health) {
    return (
      <div className="card text-center py-lg">
        <p className="text-body-md text-muted">No health data</p>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="text-title-lg font-semibold mb-lg">System Health</h3>

      <div className="grid grid-cols-5 gap-md">
        {/* Engine Status */}
        <div>
          <p className="text-caption text-muted mb-sm">Engine</p>
          <div className="flex items-center gap-sm">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                health.engine_running
                  ? 'bg-trading-up animate-pulse'
                  : 'bg-trading-down'
              }`}
            ></span>
            <span className="text-title-sm font-semibold capitalize">
              {health.engine_running ? 'Running' : 'Stopped'}
            </span>
          </div>
        </div>

        {/* Uptime */}
        <div>
          <p className="text-caption text-muted mb-sm">Uptime</p>
          <p className="text-title-sm font-semibold text-on-dark">
            {formatUptime(health.uptime_seconds)}
          </p>
        </div>

        {/* Restart Count */}
        <div>
          <p className="text-caption text-muted mb-sm">Restarts</p>
          <p
            className={`text-title-sm font-semibold ${
              health.restarts === 0 ? 'text-trading-up' : 'text-primary'
            }`}
          >
            {health.restarts}
          </p>
        </div>

        {/* Signals/Min */}
        <div>
          <p className="text-caption text-muted mb-sm">Signals/min</p>
          <p className="text-title-sm font-semibold text-on-dark">
            {health.signals_per_minute.toFixed(2)}
          </p>
        </div>

        {/* Error Count */}
        <div>
          <p className="text-caption text-muted mb-sm">Errors</p>
          <p
            className={`text-title-sm font-semibold ${
              health.error_count === 0 ? 'text-trading-up' : 'text-trading-down'
            }`}
          >
            {health.error_count}
          </p>
        </div>
      </div>

      {/* Activity Timestamps */}
      <div className="mt-lg pt-lg border-t border-hairline">
        <div className="grid grid-cols-3 gap-md">
          <div>
            <p className="text-caption text-muted mb-xs">Last Signal</p>
            <p className="text-number-sm font-mono text-on-dark">
              {formatTimestamp(health.last_signal)}
            </p>
          </div>
          <div>
            <p className="text-caption text-muted mb-xs">Last Execution</p>
            <p className="text-number-sm font-mono text-on-dark">
              {formatTimestamp(health.last_execution)}
            </p>
          </div>
          <div>
            <p className="text-caption text-muted mb-xs">Validation Rate</p>
            <p className="text-number-sm font-mono text-primary">
              {health.validation_rate}%
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
