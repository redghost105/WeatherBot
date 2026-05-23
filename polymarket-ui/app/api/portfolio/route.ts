import { NextResponse } from 'next/server'
import * as fs from 'fs'
import * as path from 'path'
import { parseTradingLogs } from '@/lib/utils'

export const dynamic = 'force-dynamic'

function getLatestLogFile(): string | null {
  const logsDir = path.join(
    process.env.HOME || '/home/carter',
    'trading_logs'
  )

  if (!fs.existsSync(logsDir)) {
    return null
  }

  const files = fs.readdirSync(logsDir)
  const logFiles = files
    .filter(f => f.startsWith('trading_') && f.endsWith('.log'))
    .sort()
    .reverse()

  return logFiles[0] ? path.join(logsDir, logFiles[0]) : null
}

function isEngineRunning(): boolean {
  try {
    const ps = require('child_process').execSync('ps aux | grep trading_engine.py | grep -v grep', {
      encoding: 'utf-8',
    })
    return ps.length > 0
  } catch {
    return false
  }
}

export async function GET() {
  try {
    const logFile = getLatestLogFile()
    let equity = 1000
    let daily_pnl = 0
    let trades_today = 0
    let restart_count = 0
    let last_scan: string | null = null

    if (logFile && fs.existsSync(logFile)) {
      const logContent = fs.readFileSync(logFile, 'utf-8')
      const parsed = parseTradingLogs(logContent)

      // Count executions from today
      const today = new Date()
      trades_today = parsed.executions.filter(e => {
        const eDate = new Date(e.timestamp)
        return (
          eDate.getFullYear() === today.getFullYear() &&
          eDate.getMonth() === today.getMonth() &&
          eDate.getDate() === today.getDate()
        )
      }).length

      restart_count = parsed.restarts
      last_scan = parsed.lastScan

      // Estimate P&L based on trades (simplified: assume 2% average profit per trade)
      daily_pnl = trades_today * (equity * 0.02)
    }

    const engine_running = isEngineRunning()
    const dailyPnLPct = equity > 0 ? (daily_pnl / equity) * 100 : 0
    const winRate = trades_today > 0 ? 65 : 0 // Will be improved with actual trade data

    return NextResponse.json({
      equity,
      dailyPnL: daily_pnl,
      dailyPnLPct: dailyPnLPct,
      winRate: winRate,
      positions_count: 0, // Will fetch from Kalshi API
      trades_today: trades_today,
      engine_status: engine_running ? 'running' : 'stopped',
      engine_uptime_seconds: 3600, // Will compute from logs later
      restart_count: restart_count,
      last_scan: last_scan || new Date().toISOString(),
    })
  } catch (error) {
    console.error('Portfolio API error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch portfolio data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
