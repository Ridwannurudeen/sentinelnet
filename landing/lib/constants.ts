export const FEATURES = [
  {
    icon: "Layers",
    title: "5-Dimension Scoring",
    description:
      "Longevity, activity, counterparty quality, contract risk, and ERC-8004 identity. Each dimension weighted and combined with sybil detection.",
  },
  {
    icon: "Link",
    title: "On-Chain Composability",
    description:
      "TrustGate contract lets other smart contracts gate execution by trust score. onlyTrusted(agentId) — one modifier, done.",
  },
  {
    icon: "Coins",
    title: "Economic Accountability",
    description:
      "ETH staked behind every published score. 72-hour challenge window. On-chain TrustDegraded events when scores drop.",
  },
  {
    icon: "HardDrive",
    title: "IPFS Evidence",
    description:
      "Full analysis JSON pinned to IPFS for every scored agent. Verifiable, immutable, auditable. Nothing hidden.",
  },
  {
    icon: "Timer",
    title: "Trust Decay",
    description:
      "Scores decay exponentially over time. A 90 becomes 67 after 30 days. Trust is earned continuously, not once.",
  },
  {
    icon: "ShieldAlert",
    title: "Sybil Detection",
    description:
      "Post-sweep cluster analysis flags coordinated agent rings. Wallet-sharing + interaction graph cliques. -20 point penalty.",
  },
  {
    icon: "Workflow",
    title: "Trust Contagion",
    description:
      "PageRank-style propagation. Interacting with malicious agents degrades your score. Trust spreads through the network — positive and negative.",
  },
  {
    icon: "Radar",
    title: "Threat Intelligence",
    description:
      "Real-time threat feed: sybil clusters, trust degradations, contagion events. Subscribe via API or MCP tool.",
  },
  {
    icon: "BadgeCheck",
    title: "EAS Attestations",
    description:
      "Every trust score becomes a verifiable Ethereum Attestation on Base. On-chain proof that survives even if SentinelNet goes offline.",
  },
] as const;

export const CONTRACTS = [
  {
    name: "SentinelNetStaking",
    address: "0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9",
    explorer: "https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9",
  },
  {
    name: "ERC-8004 Reputation Registry",
    address: "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
    explorer: "https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
  },
  {
    name: "ERC-8004 Identity Registry",
    address: "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    explorer: "https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
  },
] as const;

export const CODE_TABS = {
  Solidity: `// TrustGatedMarketplace — real integration proof
interface ITrustGate {
    function isTrusted(uint256 agentId)
        external view returns (bool);
}

contract TrustGatedMarketplace {
    ITrustGate public trustGate;

    modifier onlyTrustedAgent(uint256 agentId) {
        if (!trustGate.isTrusted(agentId))
            revert AgentNotTrusted(agentId);
        _;
    }

    function listService(
        uint256 agentId,
        string calldata desc,
        uint256 price
    ) external onlyTrustedAgent(agentId) { }
}`,
  cURL: `# Check single agent
curl https://sentinelnet.gudman.xyz/trust/31253

# Batch query
curl -X POST https://sentinelnet.gudman.xyz/trust/batch \\
  -H "Content-Type: application/json" \\
  -d '{"agent_ids": [1, 2, 3]}'

# Embed trust badge
<img src="https://sentinelnet.gudman.xyz/badge/31253.svg">`,
  Python: `import httpx

async def check_trust(agent_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://sentinelnet.gudman.xyz/trust/{agent_id}"
        )
        return r.json()

# Returns: {trust_score, verdict, explanation, ...}`,
  MCP: `{
    "name": "check_trust",
    "arguments": {
        "agent_id": 31253,
        "fresh": true
    }
}
// Also available:
// list_scored_agents, get_ecosystem_stats,
// get_score_history`,
} as const;

export const NAV_LINKS = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Marketplace", href: "/marketplace" },
  { label: "Trust Network", href: "/graph" },
  { label: "API Docs", href: "/docs" },
  { label: "Leaderboard", href: "/leaderboard" },
  { label: "GitHub", href: "https://github.com/Ridwannurudeen/sentinelnet", external: true },
] as const;
