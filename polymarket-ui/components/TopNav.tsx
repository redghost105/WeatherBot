'use client'

export function TopNav() {
  return (
    <header className="bg-canvas border-b border-hairline sticky top-0 z-50">
      <div className="px-lg py-md flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-md">
          <h1 className="text-title-lg font-bold text-primary">⚡ POLYMARKET</h1>
          <span className="text-caption text-muted">Trading Dashboard</span>
        </div>

        {/* Mode & Controls */}
        <div className="flex items-center gap-lg">
          <div className="flex items-center gap-sm">
            <span className="text-body-sm text-muted">Mode:</span>
            <span className="badge badge-warning">PAPER</span>
          </div>

          <button className="btn-secondary">
            ⚙️ Settings
          </button>
        </div>
      </div>
    </header>
  )
}
