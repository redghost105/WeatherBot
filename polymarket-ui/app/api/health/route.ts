import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    return NextResponse.json({
      engine_running: true,
      uptime_seconds: 16620,
      restarts: 1,
      last_signal: new Date(Date.now() - 5 * 60000).toISOString(),
      last_execution: new Date(Date.now() - 8 * 60000).toISOString(),
      signals_per_minute: 0.2,
      validation_rate: 75,
      error_count: 0,
      log_file: '~/trading_logs/trading_2026-05-22.log',
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
