/**
 * Utility functions for formatting and calculations
 */

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatNumber(value: number, decimals = 2): string {
  return value.toFixed(decimals)
}

export function formatTimestamp(ts: string): string {
  const date = new Date(ts)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

export function formatDate(ts: string): string {
  return new Date(ts).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatTimestampFull(ts: string): string {
  const date = new Date(ts)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  const parts = []
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)
  if (secs > 0) parts.push(`${secs}s`)

  return parts.length > 0 ? parts.join(' ') : '0s'
}

export function getSignalColor(
  recommendation: 'STRONG_BUY' | 'BUY' | 'SKIP' | 'SELL_NO'
): string {
  switch (recommendation) {
    case 'STRONG_BUY':
      return 'text-trading-up'
    case 'BUY':
      return 'text-trading-up'
    case 'SKIP':
      return 'text-primary'
    case 'SELL_NO':
      return 'text-trading-down'
    default:
      return 'text-muted'
  }
}

export function getSignalBgColor(
  recommendation: 'STRONG_BUY' | 'BUY' | 'SKIP' | 'SELL_NO'
): string {
  switch (recommendation) {
    case 'STRONG_BUY':
      return 'bg-trading-up/10'
    case 'BUY':
      return 'bg-trading-up/10'
    case 'SKIP':
      return 'bg-primary/10'
    case 'SELL_NO':
      return 'bg-trading-down/10'
    default:
      return 'bg-surface-card'
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'executed':
      return 'badge-success'
    case 'rejected':
      return 'badge-error'
    case 'pending':
      return 'badge-warning'
    default:
      return 'badge-info'
  }
}

export function getPnLColor(value: number): string {
  if (value > 0) return 'text-trading-up'
  if (value < 0) return 'text-trading-down'
  return 'text-muted'
}

export function getPnLBgColor(value: number): string {
  if (value > 0) return 'bg-trading-up/10'
  if (value < 0) return 'bg-trading-down/10'
  return 'bg-surface-card'
}

export function calculateWinRate(wins: number, total: number): number {
  if (total === 0) return 0
  return (wins / total) * 100
}

export function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

// Trading log parsing utilities
export interface TradeExecution {
  timestamp: string
  ticker: string
  buckets: string[]
  size: number
  mode: 'PAPER' | 'LIVE'
}

export interface SignalGenerated {
  timestamp: string
  ticker: string
  edge_pct: number
  confidence: number
  buckets: string[]
}

export function parseTradingLogs(content: string): {
  executions: TradeExecution[]
  signals: SignalGenerated[]
  restarts: number
  lastScan: string | null
} {
  const lines = content.split('\n')
  const executions: TradeExecution[] = []
  const signals: SignalGenerated[] = []
  let restarts = 0
  let lastScan: string | null = null

  for (const line of lines) {
    // Count engine restarts
    if (line.includes('Starting trading engine')) {
      restarts++
    }

    // Parse signal generation
    // Format: "✓ Signal generated for TICKER: edge=X.X%, confidence=Y/100"
    const signalMatch = line.match(/Signal generated for\s+([A-Za-z0-9\-]+):\s*edge=([0-9.]+)%,\s*confidence=([0-9.]+)/)
    if (signalMatch) {
      const [, ticker, edgeStr, confidenceStr] = signalMatch
      signals.push({
        timestamp: extractTimestamp(line) || new Date().toISOString(),
        ticker: ticker.trim(),
        edge_pct: parseFloat(edgeStr),
        confidence: parseFloat(confidenceStr),
        buckets: [], // Bucket info not in this log line
      })
    }

    // Parse trade executions
    // Format: "Executing TICKER: buckets | size=$X.XX | PAPER/LIVE"
    const execMatch = line.match(/Executing\s+([A-Za-z0-9\-]+):\s*([\w\-,\s]+)\s*\|\s*size=\$([0-9.]+)\s*\|\s*(PAPER|LIVE)/i)
    if (execMatch) {
      const [, ticker, bucketsStr, sizeStr, mode] = execMatch
      executions.push({
        timestamp: extractTimestamp(line) || new Date().toISOString(),
        ticker: ticker.trim(),
        buckets: bucketsStr.split(',').map(b => b.trim()),
        size: parseFloat(sizeStr),
        mode: (mode.toUpperCase() === 'LIVE' ? 'LIVE' : 'PAPER') as 'PAPER' | 'LIVE',
      })
    }

    // Parse last scan time
    const scanMatch = line.match(/Qualified\s+(\d+)\s+markets/)
    if (scanMatch) {
      lastScan = extractTimestamp(line) || new Date().toISOString()
    }
  }

  return {
    executions,
    signals,
    restarts: Math.max(0, restarts - 1), // Subtract 1 since first start isn't a restart
    lastScan,
  }
}

function extractTimestamp(logLine: string): string | null {
  // Matches formats like "2026-05-22 10:47:06,882" or "2026-05-22 10:47:06"
  const match = logLine.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/)
  if (match) {
    const [, year, month, day, hour, min, sec] = match
    return new Date(`${year}-${month}-${day}T${hour}:${min}:${sec}Z`).toISOString()
  }
  return null
}
