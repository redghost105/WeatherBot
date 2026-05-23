import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Mock data - will be replaced with log file parsing
    const signals = [
      {
        timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
        ticker: 'KXLOWTSATX-26MAY22-T71',
        edge_pct: 18.3,
        confidence: 82,
        recommendation: 'STRONG_BUY' as const,
        status: 'executed' as const,
        execution_count: 2,
        reason: 'Ensemble agreement + bias correction',
      },
      {
        timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
        ticker: 'KXLOWTZYX-T51',
        edge_pct: 12.1,
        confidence: 68,
        recommendation: 'BUY' as const,
        status: 'executed' as const,
        execution_count: 1,
        reason: 'Statistical edge detected',
      },
      {
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        ticker: 'KXTMPTZYX-T61',
        edge_pct: 8.9,
        confidence: 52,
        recommendation: 'SKIP' as const,
        status: 'rejected' as const,
        reason: 'Below minimum edge threshold (10%)',
      },
      {
        timestamp: new Date(Date.now() - 20 * 60000).toISOString(),
        ticker: 'KXDENTZYX-T45',
        edge_pct: 15.6,
        confidence: 78,
        recommendation: 'STRONG_BUY' as const,
        status: 'executed' as const,
        execution_count: 2,
        reason: 'High confidence ensemble signal',
      },
      {
        timestamp: new Date(Date.now() - 25 * 60000).toISOString(),
        ticker: 'KXLAXTZYX-T32',
        edge_pct: 9.2,
        confidence: 45,
        recommendation: 'SKIP' as const,
        status: 'rejected' as const,
        reason: 'Confidence below minimum (55)',
      },
    ]

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
