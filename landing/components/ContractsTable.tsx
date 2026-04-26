import { CONTRACTS } from "@/lib/constants";

export default function ContractsTable() {
  return (
    <section className="py-24 px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-10 max-w-2xl">
          <p className="text-sm text-muted mb-4">Verifiable</p>
          <h2
            className="font-display font-light text-text"
            style={{ fontSize: "clamp(1.75rem, 4vw, 2.75rem)", lineHeight: "1.1", letterSpacing: "-0.03em" }}
          >
            Live contracts on Base mainnet.
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {CONTRACTS.map((c) => (
            <a
              key={c.address}
              href={c.explorer}
              target="_blank"
              rel="noopener noreferrer"
              className="group surface-card rounded-2xl p-5 hover:border-text/40 transition-colors"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <h3 className="text-text font-medium">{c.name}</h3>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-muted group-hover:text-text transition-colors mt-1"
                >
                  <path d="M7 17L17 7M7 7h10v10" />
                </svg>
              </div>
              <code className="ticker text-xs text-muted break-all">
                {c.address}
              </code>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
