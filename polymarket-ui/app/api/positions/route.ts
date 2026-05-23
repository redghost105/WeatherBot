import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Mock data - will be replaced with Kalshi API call
    const positions = [
      {
        ticker: 'KXLOWTSATX-26MAY22-T71',
        side: 'YES' as const,
        quantity: 2,
        entry_price: 0.5,
        current_price: 0.56,
        exposure: 2.34,
        realized_pnl: 0.12,
        edge_pct: 17.3,
        confidence: 82,
        market_name: 'NYC Low Temperature 71-72°F',
      },
      {
        ticker: 'KXLOWTZYX-T51',
        side: 'NO' as const,
        quantity: 1,
        entry_price: 0.48,
        current_price: 0.45,
        exposure: 1.12,
        realized_pnl: 3.45,
        edge_pct: 11.2,
        confidence: 71,
        market_name: 'Chicago Low Temperature 51-52°F',
      },
    ]

    return NextResponse.json(positions)
  } catch (error) {
    console.error('Positions API error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch positions',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
