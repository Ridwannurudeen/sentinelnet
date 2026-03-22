# SentinelNet — The Trust Layer for ERC-8004 Agents on Base

## One-liner

Autonomous reputation watchdog that scored 3,098 agents, flagged 1,642 sybils, and logged 3,387 threats — zero human involvement.

## What it does

SentinelNet is a live infrastructure layer that continuously discovers, analyzes, and scores every ERC-8004 agent on Base. It runs 24/7 as Agent #31253, scanning the full registry of 35,000+ agents with 5-dimensional trust analysis, sybil detection, trust contagion propagation, and verifiable evidence pinned to IPFS.

Any agent or contract can query SentinelNet before transacting with an unknown counterparty. One API call returns a trust score backed by on-chain proof and staked ETH.

## The problem

35,000+ agents are registered on the ERC-8004 Identity Registry. Any agent can register. There is no built-in mechanism to distinguish trustworthy agents from sybils, scammers, or agents interacting with malicious contracts. As the agent economy scales, it collapses without trust infrastructure.

## What we found

This is not theoretical. SentinelNet found real threats in the wild:

- **1,642 sybil agents** across 67 wallets — one wallet registered 10+ agents, all sharing the same address (`0x0049dCe82B...`). SentinelNet flagged them autonomously, applied -20 sybil penalty, and crushed all to score 0.
- **859 sybil clusters** detected through dual-method analysis (wallet-sharing + interaction graph cliques)
- **3,387 threat events** logged — sybil clusters, trust degradations, and trust contagion spreading through the interaction graph
- **1,804 agents REJECTED** (66% of scored agents) — the ERC-8004 ecosystem has a trust problem, and SentinelNet quantifies it

## How it works

1. **Discover** — Progressive full-registry sweep of all 35K+ agents (cursor-based batches, every 30 min)
2. **Analyze** — 5-dimensional scoring: Longevity (15%), Activity (20%), Counterparty Quality (20%), Contract Risk (20%), Agent Identity (25%)
3. **Detect** — Dual-method sybil detection (wallet-sharing + graph cliques) + PageRank-style trust contagion
4. **Publish** — Pin evidence to IPFS, write reputation feedback on-chain, stake ETH behind every score
5. **Alert** — Emit on-chain TrustDegraded events, fire webhooks, stream via WebSocket

## Integration paths

- **Smart Contract**: [`TrustGate.sol`](https://basescan.org/address/0x985f68c98b0d1BB9B378D969C360783B64cfA4EB) — `require(gate.isTrusted(agentId))` in any contract
- **Python SDK**: `pip install sentinelnet` — `SentinelNet().is_trusted(42)`
- **JavaScript SDK**: `npm install sentinelnet`
- **REST API**: `GET /trust/{agent_id}` — 20+ endpoints with rate limiting
- **MCP**: 5 tools for agent-to-agent trust queries
- **WebSocket**: `ws://host/ws/scores` — real-time score stream
- **Webhooks**: Subscribe to trust change notifications
- **Prometheus**: `/metrics` for production monitoring

## Live deployment

Everything is running in production right now:

- **Landing**: https://sentinelnet.gudman.xyz
- **Dashboard**: https://sentinelnet.gudman.xyz/dashboard
- **Marketplace**: https://sentinelnet.gudman.xyz/marketplace
- **Trust Network**: https://sentinelnet.gudman.xyz/graph
- **Leaderboard**: https://sentinelnet.gudman.xyz/leaderboard
- **API Docs**: https://sentinelnet.gudman.xyz/docs
- **Metrics**: https://sentinelnet.gudman.xyz/metrics
- **Anomalies**: https://sentinelnet.gudman.xyz/api/anomalies
- **Threat Feed**: https://sentinelnet.gudman.xyz/api/threats

## On-chain artifacts

| Artifact | Address |
|----------|---------|
| Agent #31253 | [Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |
| Reputation feedback | [Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) |
| Score staking | [SentinelNetStaking](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9) |
| Trust gate | [TrustGate](https://basescan.org/address/0x985f68c98b0d1BB9B378D969C360783B64cfA4EB) |
| Evidence | IPFS via Pinata (CID per agent) |

## Tech stack

Python 3.11+ / FastAPI / SQLite WAL / web3.py / Next.js / Tailwind / Framer Motion / D3.js / Solidity 0.8.24 / MCP / IPFS / EAS

## By the numbers

| Metric | Value |
|--------|-------|
| Agents scored | 3,098 |
| Scores on-chain | 3,098 (via TrustGate) |
| Sybil agents flagged | 1,642 |
| Sybil clusters detected | 859 |
| Threats logged | 3,387 |
| Agents rejected | 1,804 (66%) |
| On-chain txs (paymaster) | 64 |
| Tests passing | 100 |
| API endpoints | 20+ |
| MCP tools | 5 |
| Integration paths | 8 (Contract, Python, JS, REST, MCP, WebSocket, Webhook, Prometheus) |

## Roadmap

- **Multi-ecosystem scoring** — Virtual Protocol agents (Base), Autonolas/Olas autonomous services, ai16z/ElizaOS agents
- **Cross-chain trust** — Extend TrustGate to Ethereum L1, Arbitrum, Optimism
- **Trust-gated DeFi** — Lending protocols gate borrowing by agent trust score
- **Decay-aware on-chain scores** — Move exponential decay logic into the smart contract
- **DAO governance** — Community-driven threshold tuning and dispute resolution
- **Token-gated API tiers** — Premium endpoints for high-frequency consumers

## GitHub

https://github.com/Ridwannurudeen/sentinelnet
