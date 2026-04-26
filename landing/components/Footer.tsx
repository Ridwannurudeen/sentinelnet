export default function Footer() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="max-w-6xl mx-auto px-6 lg:px-8 py-12 grid grid-cols-1 sm:grid-cols-12 gap-8">
        <div className="sm:col-span-5">
          <span
            className="font-display text-3xl font-light text-text"
            style={{ letterSpacing: "-0.05em" }}
          >
            SN
          </span>
          <p className="mt-3 text-sm text-muted max-w-xs font-light leading-relaxed">
            Reputation, on-chain, for every agent. Live on Base mainnet as ERC-8004 Agent #37506.
          </p>
        </div>
        <div className="sm:col-span-3">
          <p className="text-xs uppercase tracking-widest text-muted mb-3">Product</p>
          <ul className="space-y-2 text-sm">
            <li><a href="/dashboard" className="text-text hover:text-text/70">Dashboard</a></li>
            <li><a href="/marketplace" className="text-text hover:text-text/70">Marketplace</a></li>
            <li><a href="/graph" className="text-text hover:text-text/70">Trust network</a></li>
            <li><a href="/leaderboard" className="text-text hover:text-text/70">Leaderboard</a></li>
          </ul>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs uppercase tracking-widest text-muted mb-3">Build</p>
          <ul className="space-y-2 text-sm">
            <li><a href="/docs" className="text-text hover:text-text/70">API</a></li>
            <li><a href="/methodology" className="text-text hover:text-text/70">Methodology</a></li>
            <li><a href="https://github.com/Ridwannurudeen/sentinelnet" target="_blank" rel="noopener noreferrer" className="text-text hover:text-text/70">GitHub</a></li>
          </ul>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs uppercase tracking-widest text-muted mb-3">Status</p>
          <ul className="space-y-2 text-sm">
            <li className="text-text inline-flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-trust animate-pulse" />Operational</li>
            <li className="text-muted">Base mainnet</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 lg:px-8 py-5 text-xs text-muted flex flex-col sm:flex-row gap-2 justify-between">
          <span>© {new Date().getFullYear()} SentinelNet</span>
          <span>Open source — MIT licensed</span>
        </div>
      </div>
    </footer>
  );
}
