import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Generate mock equity timeline for 24 hours
    const now = new Date()
    const startOfDay = new Date(now)
    startOfDay.setHours(0, 0, 0, 0)

    const timeline = []
    let currentEquity = 1000

    // Generate 288 data points (one every 5 minutes for 24 hours)
    for (let i = 0; i < 288; i++) {
      const timestamp = new Date(startOfDay.getTime() + i * 5 * 60000)
      // Random walk with slight upward drift
      currentEquity += (Math.random() - 0.48) * 5
      timeline.push({
        timestamp: timestamp.toISOString(),
        equity: Math.max(currentEquity, 950),
      })
    }

    // Daily bars (mock)
    const daily_bars = [
      { date: '2026-05-20', pnl: -45.23, trades: 3 },
      { date: '2026-05-21', pnl: 67.89, trades: 5 },
      { date: '2026-05-22', pnl: 87.34, trades: 5 },
    ]

    return NextResponse.json({
      timeline,
      daily_bars,
    })
  } catch (error) {
    console.error('Performance API error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch performance data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
