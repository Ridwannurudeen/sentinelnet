"use client";

import { useState } from "react";

type Stack = "solidity" | "python" | "rest" | "mcp";

const STACKS: { key: Stack; label: string; sub: string }[] = [
  { key: "solidity", label: "Solidity", sub: "Smart contract gating" },
  { key: "python", label: "Python", sub: "Async SDK" },
  { key: "rest", label: "REST", sub: "Any language" },
  { key: "mcp", label: "MCP", sub: "Claude / Cursor agents" },
];

const SNIPPETS: Record<Stack, { install: string; use: string; verify: string }> = {
  solidity: {
    install: `// 1. No install — just import the interface
interface ITrustGate {
  function isTrusted(uint256 agentId)
    external view returns (bool);
}`,
    use: `// 2. Add the modifier to any function
contract MyAgentMarketplace {
  ITrustGate public gate =
    ITrustGate(0xE3b6069f632ab439ef5B084C769F21b4beeE3506);

  modifier onlyTrusted(uint256 agentId) {
    require(gate.isTrusted(agentId), "untrusted agent");
    _;
  }

  function listService(uint256 agentId, string calldata desc)
    external onlyTrusted(agentId)
  { /* ... */ }
}`,
    verify: `// 3. That's it. The next call from a REJECT-rated
// agent will revert. Live on Base mainnet.`,
  },
  python: {
    install: `# 1. Install
pip install httpx`,
    use: `# 2. One async call
import httpx

async def is_trusted(agent_id: int) -> bool:
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"https://sentinelnet.gudman.xyz/trust/{agent_id}"
        )
        return r.json()["verdict"] == "TRUST"`,
    verify: `# 3. Use the result
if await is_trusted(37506):
    proceed()
else:
    reject_with_reason("untrusted agent")`,
  },
  rest: {
    install: `# 1. No install — just curl
# Single agent
curl https://sentinelnet.gudman.xyz/trust/31253`,
    use: `# 2. Batch query
curl -X POST https://sentinelnet.gudman.xyz/trust/batch \\
  -H "Content-Type: application/json" \\
  -d '{"agent_ids": [1, 2, 3, 37506]}'`,
    verify: `# 3. Embed a trust badge anywhere
<img src="https://sentinelnet.gudman.xyz/badge/37506.svg">`,
  },
  mcp: {
    install: `// 1. Add to your Claude / Cursor MCP config
{
  "mcpServers": {
    "sentinelnet": {
      "url": "https://sentinelnet.gudman.xyz/mcp"
    }
  }
}`,
    use: `// 2. Tools your agent now has
//   check_trust(agent_id, fresh?)
//   list_scored_agents(limit?)
//   get_ecosystem_stats()
//   get_score_history(agent_id)`,
    verify: `// 3. Your agent can now ask:
//   "Is agent 37506 trusted right now?"
// and get a live, on-chain-verified answer.`,
  },
};

export default function GetStartedFlow() {
  const [active, setActive] = useState<Stack>("solidity");
  const snip = SNIPPETS[active];

  return (
    <section className="py-12 px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
          {STACKS.map((s) => (
            <button
              key={s.key}
              onClick={() => setActive(s.key)}
              className={`flex flex-col items-start gap-0.5 px-5 py-3 rounded-2xl border transition-all ${
                active === s.key
                  ? "bg-text text-bg border-text"
                  : "bg-bg text-text border-border hover:border-text/40"
              }`}
            >
              <span className="text-sm font-medium">{s.label}</span>
              <span className={`text-xs ${active === s.key ? "text-bg/70" : "text-muted"}`}>
                {s.sub}
              </span>
            </button>
          ))}
        </div>

        <div className="space-y-6">
          {[
            { n: "01", title: "Install", body: snip.install },
            { n: "02", title: "Use", body: snip.use },
            { n: "03", title: "Verify", body: snip.verify },
          ].map((step) => (
            <div key={step.n} className="grid grid-cols-1 sm:grid-cols-12 gap-4">
              <div className="sm:col-span-3">
                <div className="flex items-baseline gap-3">
                  <span className="ticker text-muted text-sm">{step.n}</span>
                  <h3
                    className="font-display font-light text-text"
                    style={{ fontSize: "1.5rem", letterSpacing: "-0.02em" }}
                  >
                    {step.title}
                  </h3>
                </div>
              </div>
              <div className="sm:col-span-9">
                <pre className="surface-card rounded-2xl p-5 sm:p-6 overflow-x-auto font-mono text-sm leading-relaxed text-text/90">
                  <code>{step.body}</code>
                </pre>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16 surface-card rounded-3xl p-8 sm:p-10">
          <h3
            className="font-display font-light text-text mb-3"
            style={{ fontSize: "1.65rem", letterSpacing: "-0.02em" }}
          >
            Ready?
          </h3>
          <p className="text-muted text-sm font-light leading-relaxed max-w-md mb-6">
            Try a real trust query against the live API right now, or open the
            full docs to see every endpoint, schema, and SDK method.
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href="/trust/37506"
              className="inline-flex items-center gap-2 h-11 px-5 rounded-full bg-text text-bg text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Try a live query
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
            </a>
            <a
              href="/docs"
              className="inline-flex items-center h-11 px-5 rounded-full border border-border hover:border-text/40 text-text text-sm font-medium transition-colors"
            >
              Full API docs
            </a>
            <a
              href="/dashboard"
              className="inline-flex items-center h-11 px-5 rounded-full border border-border hover:border-text/40 text-text text-sm font-medium transition-colors"
            >
              Live dashboard
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
