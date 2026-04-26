const PILLARS = [
  {
    label: "Identity",
    bg: "pastel-blue",
    title: "ERC-8004 native",
    body:
      "Every scored agent is registered through the canonical Identity Registry. Deterministic, portable, addressable from any contract on Base.",
  },
  {
    label: "Reputation",
    bg: "pastel-peach",
    title: "Five-dimensional, slashable",
    body:
      "Longevity, activity, counterparty, contract risk, identity quality — combined into a single score backed by staked ETH and challengeable for 72 hours.",
  },
  {
    label: "Validation",
    bg: "pastel-sage",
    title: "Composable in one line",
    body:
      "isTrusted(agentId) is callable from any Solidity contract. Add a single modifier and your dApp gates execution by live agent reputation.",
  },
];

export default function ThreePillars() {
  return (
    <section className="py-24 sm:py-32 px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="max-w-2xl mb-16">
          <p className="text-sm text-muted mb-4">What it is</p>
          <h2
            className="font-display font-light text-text"
            style={{
              fontSize: "clamp(2rem, 5vw, 3.5rem)",
              lineHeight: "1.05",
              letterSpacing: "-0.03em",
            }}
          >
            The trust spine for the
            <br />
            <span className="italic">agent economy on Base.</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
          {PILLARS.map((p) => (
            <article
              key={p.label}
              className={`${p.bg} rounded-3xl p-7 sm:p-9 transition-transform duration-300 hover:-translate-y-1`}
            >
              <p className="text-xs uppercase tracking-widest text-text/60 mb-6">
                {p.label}
              </p>
              <h3
                className="font-display font-light text-text mb-4"
                style={{ fontSize: "1.65rem", lineHeight: "1.15", letterSpacing: "-0.02em" }}
              >
                {p.title}
              </h3>
              <p className="text-sm text-text/70 leading-relaxed font-light">
                {p.body}
              </p>
            </article>
          ))}
        </div>

        <p className="mt-10 text-sm text-muted max-w-3xl font-light leading-relaxed">
          <span className="text-text">Plus:</span> 5-dimension scoring · IPFS-pinned evidence · 72h challenge window · trust contagion via PageRank · paymaster gasless writes · Prometheus metrics · Python &amp; JS SDKs · MCP server.
        </p>
      </div>
    </section>
  );
}
