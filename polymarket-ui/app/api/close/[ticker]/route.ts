import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function POST(
  request: Request,
  { params }: { params: { ticker: string } }
) {
  try {
    const { ticker } = params

    // TODO: Call Kalshi API to execute market sell order
    // For now, return mock success response

    return NextResponse.json({
      success: true,
      ticker: ticker,
      side: 'YES',
      quantity: 2,
      executed_price: 0.57,
      order_id: `ord_${Date.now()}`,
    })
  } catch (error) {
    console.error(`Close position API error for ${params.ticker}:`, error)
    return NextResponse.json(
      {
        error: 'Failed to close position',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
