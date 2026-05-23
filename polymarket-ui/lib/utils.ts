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
