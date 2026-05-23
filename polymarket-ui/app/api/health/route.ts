import { NextResponse } from 'next/server'
import * as fs from 'fs'
import * as path from 'path'
import { parseTradingLogs } from '@/lib/utils'
import { execSync } from 'child_process'

export const dynamic = 'force-dynamic'

function isEngineRunning(): boolean {
  try {
    const ps = execSync('ps aux | grep trading_engine.py | grep -v grep', {
      encoding: 'utf-8',
    })
    return ps.length > 0
  } catch {
    return false
  }
}

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

export async function GET() {
  try {
    const engine_running = isEngineRunning()
    const logFile = getLatestLogFile()

    let uptime_seconds = 0
    let restarts = 0
    let last_signal: string | null = null
    let last_execution: string | null = null
    let signals_per_minute = 0
    let validation_rate = 75
    let error_count = 0
    let log_file = logFile || '~/trading_logs/trading_YYYY-MM-DD.log'

    if (logFile && fs.existsSync(logFile)) {
      const logContent = fs.readFileSync(logFile, 'utf-8')
      const parsed = parseTradingLogs(logContent)

      restarts = parsed.restarts

      // Get timestamps for last signal and execution
      if (parsed.signals.length > 0) {
        last_signal = parsed.signals[parsed.signals.length - 1].timestamp
      }
      if (parsed.executions.length > 0) {
        last_execution = parsed.executions[parsed.executions.length - 1].timestamp
      }

      // Estimate uptime from log file modification time
      const stats = fs.statSync(logFile)
      const logModTime = new Date(stats.mtimeMs)
      const now = new Date()
      uptime_seconds = Math.floor((now.getTime() - logModTime.getTime()) / 1000)

      // Calculate signals per minute (last hour)
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000)
      const signalsInLastHour = parsed.signals.filter(s =>
        new Date(s.timestamp) > oneHourAgo
      ).length
      signals_per_minute = signalsInLastHour > 0 ? signalsInLastHour / 60 : 0

      // Count errors in logs
      const errorLines = logContent.split('\n').filter(
        l =>
          l.toLowerCase().includes('error') ||
          l.toLowerCase().includes('failed') ||
          l.toLowerCase().includes('exception')
      )
      error_count = errorLines.length
    }

    return NextResponse.json({
      engine_running,
      uptime_seconds,
      restarts,
      last_signal,
      last_execution,
      signals_per_minute: Math.round(signals_per_minute * 100) / 100,
      validation_rate,
      error_count,
      log_file,
    })
  } catch (error) {
    console.error('Health API error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch health status',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
