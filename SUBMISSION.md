# SentinelNet — The Trust Layer for ERC-8004 Agents on Base

## One-liner

Autonomous reputation watchdog that scored 3,769+ agents, unmasked 84 sybil networks controlling 2,119+ fake agents, and rejected 73% of the ecosystem — zero human involvement.

## What it does

SentinelNet is a live infrastructure layer that continuously discovers, analyzes, and scores every ERC-8004 agent on Base. It runs 24/7 as Agent #31253, scanning the full registry of 35,000+ agents with 5-dimensional trust analysis, sybil detection, trust contagion propagation, and verifiable evidence pinned to IPFS.

Any agent or contract can query SentinelNet before transacting with an unknown counterparty. One API call returns a trust score backed by on-chain proof and staked ETH.

## The problem

35,000+ agents are registered on the ERC-8004 Identity Registry. Any agent can register. There is no built-in mechanism to distinguish trustworthy agents from sybils, scammers, or agents interacting with malicious contracts. As the agent economy scales, it collapses without trust infrastructure.

## What we found

This is not theoretical. SentinelNet found real threats in the live ERC-8004 ecosystem:

### The 260-Agent Sybil Network

One wallet (`0x67722c...`) registered **260 agents** — 88% with sequential IDs, a textbook mass-registration attack. SentinelNet flagged 253 as sybil, applied the -20 penalty, and REJECTED 254 of them. Without SentinelNet, any protocol composing with ERC-8004 would treat these 260 fake agents as legitimate.

### The Full Picture

- **84 sybil networks** detected — the top 3 operators alone control 502 fake agents
- **2,119+ sybil agents** flagged (56% of all agents are sybils)
- **754 agents** hit by trust contagion — penalized an average of -11 points for associating with flagged counterparties
- **259 ghost agents** with zero activity and zero longevity — registered but never transacted
- **2,743 agents REJECTED** (73% of scored agents)
- **Ecosystem health score: 26/100** — the ERC-8004 registry has a trust crisis, and SentinelNet is the only system quantifying it

No human flagged these threats. No one curated a blocklist. Agent #31253 discovered, analyzed, and published every finding autonomously.

## How it works

1. **Discover** — Progressive full-registry sweep of all 35K+ agents (cursor-based batches, every 30 min)
2. **Analyze** — 5-dimensional scoring: Longevity (15%), Activity (20%), Counterparty Quality (20%), Contract Risk (20%), Agent Identity (25%)
3. **Detect** — Dual-method sybil detection (wallet-sharing + graph cliques) + PageRank-style trust contagion
4. **Publish** — Pin evidence to IPFS, write reputation feedback on-chain via gasless CDP Paymaster, stake ETH behind every score via direct EOA transactions
5. **Alert** — Emit on-chain TrustDegraded events, fire webhooks, stream via WebSocket

## What makes this different

- **Fully autonomous** — Agent #31253 runs 24/7 with zero human involvement. No curation, no moderation queue, no manual reviews. It discovers, scores, and publishes on its own.
- **Real data, real threats** — This is not a mockup or a demo with seeded data. SentinelNet found 2,119+ actual sybils operating across 84 networks, and flagged every one of them.
- **8 integration paths** — Any protocol can plug in however they want: smart contract, Python SDK, JavaScript SDK, REST API, MCP, WebSocket, webhooks, or Prometheus. No vendor lock-in.
- **On-chain verifiability** — Every trust score is backed by a TrustGate contract call, IPFS-pinned evidence, and staked ETH. Nothing is hand-waved.
- **Gasless via Coinbase CDP Paymaster** — Reputation feedback and staking operations submitted gaslessly via ERC-4337 Smart Account with sponsored gas (355+ UserOperations sent). TrustGate oracle uses direct EOA transactions on Base.
- **Trust contagion** — PageRank-style propagation through the agent interaction graph. If an agent transacts with flagged counterparties, its score degrades automatically. Trust is earned through the network, not declared.

## Integration paths

- **Smart Contract**: [`TrustGate.sol`](https://basescan.org/address/0x10D8caC126849123Cc1fb5806054be6c90343CC8) — `require(gate.isTrusted(agentId))` in any contract
- **Python SDK**: `pip install ./sdk/python` or import from `sdk/python/sentinelnet/` — `SentinelNet().is_trusted(42)`
- **JavaScript SDK**: `npm install ./sdk/js` or import from `sdk/js/src/`
- **REST API**: `GET /trust/{agent_id}` — 27 endpoints with rate limiting
- **MCP**: 8 tools for agent-to-agent trust queries
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
- **API Docs**: https://sentinelnet.gudman.xyz/docs-guide
- **Metrics**: https://sentinelnet.gudman.xyz/metrics
- **Anomalies**: https://sentinelnet.gudman.xyz/api/anomalies
- **Threat Feed**: https://sentinelnet.gudman.xyz/api/threats

## On-chain artifacts

| Artifact | Address |
|----------|---------|
| Agent #31253 | [Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |
| Reputation feedback | [Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) |
| Score staking | [SentinelNetStaking](https://basescan.org/address/0xEe1A8f34F1320D534b9a547f882762EABCB4f96d) |
| Trust gate | [TrustGate](https://basescan.org/address/0x10D8caC126849123Cc1fb5806054be6c90343CC8) |
| Evidence | IPFS / API (full analysis JSON per agent) |

## Tech stack

Python 3.11+ / FastAPI / SQLite WAL / web3.py / Coinbase CDP SDK / ERC-4337 Smart Account / Next.js / Tailwind / Framer Motion / D3.js / Solidity 0.8.24 / MCP / IPFS

## By the numbers

| | |
|---|---|
| **3,769+** agents scored | **84** sybil networks unmasked |
| **2,119+** sybils flagged (56%) | **754** contagion-penalized agents |
| **2,743** agents rejected (73%) | **259** ghost agents identified |
| **355+** on-chain UserOps via CDP Paymaster | **147** tests passing |
| **27** API endpoints | **8** MCP tools |
| **8** integration paths | **0** humans in the loop |

## Roadmap

- **Multi-ecosystem scoring** — Virtual Protocol agents (Base), Autonolas/Olas autonomous services, ai16z/ElizaOS agents
- **Cross-chain trust** — Extend TrustGate to Ethereum L1, Arbitrum, Optimism
- **Trust-gated DeFi** — Lending protocols gate borrowing by agent trust score
- **Decay-aware on-chain scores** — Move exponential decay logic into the smart contract
- **DAO governance** — Community-driven threshold tuning and dispute resolution
- **Token-gated API tiers** — Premium endpoints for high-frequency consumers

## GitHub

https://github.com/Ridwannurudeen/sentinelnet
