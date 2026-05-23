'use client'

import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { PerformanceData } from '@/lib/api-client'
import { formatCurrency, formatTimestamp } from '@/lib/utils'

interface EquityCurveProps {
  data?: PerformanceData
  loading?: boolean
}

export function EquityCurve({ data, loading }: EquityCurveProps) {
  const chartData = useMemo(() => {
    if (!data?.timeline) return []

    // Sample every nth point to avoid overcrowding (show ~50 points max)
    const sampleRate = Math.ceil(data.timeline.length / 50)
    return data.timeline
      .filter((_, idx) => idx % sampleRate === 0)
      .map((point) => ({
        ...point,
        displayTime: formatTimestamp(point.timestamp),
      }))
  }, [data?.timeline])

  if (loading) {
    return (
      <div className="card h-80 animate-pulse">
        <div className="bg-hairline h-full rounded"></div>
      </div>
    )
  }

  if (!data || chartData.length === 0) {
    return (
      <div className="card h-80 flex items-center justify-center">
        <p className="text-muted">No equity data available</p>
      </div>
    )
  }

  const minEquity = Math.min(...data.timeline.map((p) => p.equity))
  const maxEquity = Math.max(...data.timeline.map((p) => p.equity))

  return (
    <div className="card">
      <h3 className="text-title-lg font-semibold mb-md">Equity Curve (24h)</h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#2b3139"
            vertical={false}
          />
          <XAxis
            dataKey="displayTime"
            stroke="#707a8a"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#707a8a' }}
          />
          <YAxis
            stroke="#707a8a"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#707a8a' }}
            domain={[
              Math.floor(minEquity / 10) * 10,
              Math.ceil(maxEquity / 10) * 10,
            ]}
            tickFormatter={(value) => formatCurrency(value).slice(0, -3)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e2329',
              border: '1px solid #2b3139',
              borderRadius: '6px',
              padding: '12px',
            }}
            labelStyle={{ color: '#eaecef' }}
            formatter={(value: number) => [formatCurrency(value), 'Equity']}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#0ecb81"
            dot={false}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Daily bars summary */}
      {data.daily_bars && data.daily_bars.length > 0 && (
        <div className="mt-lg pt-lg border-t border-hairline">
          <h4 className="text-title-sm font-semibold mb-md">Daily Summary</h4>
          <div className="grid grid-cols-3 gap-md">
            {data.daily_bars.slice(-3).map((bar) => (
              <div key={bar.date} className="p-md bg-surface-elevated rounded-lg">
                <p className="text-caption text-muted mb-xs">{bar.date}</p>
                <p
                  className={`text-number-md font-mono ${
                    bar.pnl >= 0 ? 'text-trading-up' : 'text-trading-down'
                  }`}
                >
                  {bar.pnl >= 0 ? '+' : ''}
                  {formatCurrency(bar.pnl)}
                </p>
                <p className="text-caption text-muted">{bar.trades} trades</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
