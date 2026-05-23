import { NextResponse } from 'next/server'
import * as fs from 'fs'
import * as path from 'path'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Read from trading engine state file
    const stateFile = path.join(
      process.env.HOME || '/home/carter',
      'claude_programs/Polymarket/engine-state.json'
    )

    let engineState = {
      equity: 1000,
      daily_pnl: 0,
      trades_today: 0,
      engine_running: true,
      engine_uptime_seconds: 0,
      restart_count: 0,
      last_scan: new Date().toISOString(),
    }

    // Try to read actual state file if it exists
    if (fs.existsSync(stateFile)) {
      try {
        const content = fs.readFileSync(stateFile, 'utf-8')
        engineState = JSON.parse(content)
      } catch (e) {
        console.log('Could not parse engine state file, using defaults')
      }
    }

    // Calculate derived metrics
    const winRate = engineState.trades_today > 0 ? 65 : 0 // Mock calculation
    const dailyPnLPct =
      engineState.equity > 0
        ? (engineState.daily_pnl / engineState.equity) * 100
        : 0

    return NextResponse.json({
      equity: engineState.equity,
      dailyPnL: engineState.daily_pnl,
      dailyPnLPct: dailyPnLPct,
      winRate: winRate,
      positions_count: 2, // Will be fetched from Kalshi API in Phase 2
      trades_today: engineState.trades_today,
      engine_status: engineState.engine_running ? 'running' : 'stopped',
      engine_uptime_seconds: engineState.engine_uptime_seconds,
      restart_count: engineState.restart_count,
      last_scan: engineState.last_scan,
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
