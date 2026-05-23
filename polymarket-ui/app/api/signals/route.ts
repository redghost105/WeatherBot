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

export async function GET() {
  try {
    const signals = []
    const logFile = getLatestLogFile()

    if (logFile && fs.existsSync(logFile)) {
      const logContent = fs.readFileSync(logFile, 'utf-8')
      const parsed = parseTradingLogs(logContent)

      // Convert parsed signals to API response format
      for (const sig of parsed.signals.slice(0, 20)) {
        // Determine status based on whether it was executed
        const wasExecuted = parsed.executions.some(e =>
          e.ticker === sig.ticker &&
          new Date(e.timestamp) >= new Date(sig.timestamp)
        )

        let recommendation: 'STRONG_BUY' | 'BUY' | 'SKIP' | 'SELL_NO' = 'SKIP'
        if (sig.edge_pct >= 15) {
          recommendation = 'STRONG_BUY'
        } else if (sig.edge_pct >= 10) {
          recommendation = 'BUY'
        }

        signals.push({
          timestamp: sig.timestamp,
          ticker: sig.ticker,
          edge_pct: sig.edge_pct,
          confidence: sig.confidence,
          recommendation,
          status: wasExecuted ? 'executed' : 'pending',
          execution_count: wasExecuted ? 1 : 0,
          reason: sig.confidence >= 75
            ? 'High confidence signal'
            : sig.confidence >= 55
            ? 'Moderate confidence signal'
            : 'Low confidence signal',
        })
      }
    } else {
      // Fallback to mock data if no logs available
      signals.push({
        timestamp: new Date().toISOString(),
        ticker: 'KTEST',
        edge_pct: 12.5,
        confidence: 68,
        recommendation: 'BUY',
        status: 'pending',
        execution_count: 0,
        reason: 'Awaiting favorable market conditions',
      })
    }

    return NextResponse.json(signals)
  } catch (error) {
    console.error('Signals API error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch signals',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
