# SentinelNet Roadmap

> Autonomous Agent Reputation Watchdog for ERC-8004 on Base

Last updated: March 27, 2026

---

## Where We Are Today

SentinelNet is a fully autonomous reputation system scoring 3,700+ ERC-8004 agents on Base. It runs 24/7 with zero human intervention — discovering agents, analyzing on-chain behavior across Base and Ethereum, detecting sybil networks, propagating trust contagion, publishing verifiable evidence to IPFS, and writing composable reputation feedback on-chain.

**Key numbers:**
- 3,769 agents scored across 5 behavioral dimensions
- 84 sybil networks detected, 2,119 sybil agents flagged (56% of ecosystem)
- 754 agents penalized via trust contagion propagation
- 8 integration paths (smart contract, Python SDK, JS SDK, REST, MCP, WebSocket, webhooks, Prometheus)
- 2 deployed contracts (TrustGate oracle + SentinelNetStaking)
- 147 tests passing

---

## Phase 1: Foundation Hardening (Q2 2026)

*Make what exists bulletproof before expanding scope.*

### SDK Publishing
- [ ] Publish Python SDK to PyPI (`pip install sentinelnet`)
- [ ] Publish JavaScript SDK to npm (`npm install sentinelnet`)
- [ ] Add versioned API documentation (OpenAPI spec already exists at `/docs`)
- [ ] Write integration guides with code examples for each path

### Scoring Improvements
- [ ] Internal transaction analysis (traces, not just top-level transfers)
- [ ] Failed transaction pattern detection (repeated reverts = suspicious)
- [ ] Gas usage profiling (abnormal gas patterns as a signal)
- [ ] Contract verification status weighting (verified source on Basescan = trust boost)
- [ ] Historical score calibration — backtest scoring model against known-good and known-bad agents

### Operational Resilience
- [ ] Multi-RPC failover (Base: Alchemy, QuickNode, LlamaRPC fallback chain)
- [ ] IPFS pinning redundancy (Pinata primary, Lighthouse backup, local IPFS node tertiary)
- [ ] Database migration from SQLite to PostgreSQL for concurrent writes and better durability
- [ ] Structured logging with log aggregation (Loki or similar)
- [ ] Automated alerting on agent downtime, scoring failures, and wallet balance depletion

### Challenge System Activation
- [ ] Build challenger bot that monitors staked scores and disputes outliers
- [ ] Implement dispute resolution pipeline (evidence submission, voting, slash/reward)
- [ ] Deploy challenger pool contract for community participation
- [ ] Document the challenge economics (stake amounts, slash ratios, reward distribution)

---

## Phase 2: Multi-Ecosystem Expansion (Q3 2026)

*Score agents beyond ERC-8004 — wherever AI agents operate on-chain.*

### Cross-Chain TrustGate
- [ ] Deploy TrustGate oracle on Ethereum L1
- [ ] Deploy TrustGate oracle on Arbitrum
- [ ] Deploy TrustGate oracle on Optimism
- [ ] Implement cross-chain score synchronization (Base as source of truth, L2s as mirrors)
- [ ] Add chain-specific scoring adjustments (different ecosystems have different baselines)

### Multi-Protocol Agent Discovery
- [ ] Autonolas/Olas service agent scoring (discover via Olas registry, map to wallets)
- [ ] Virtual Protocol agent scoring (Virtual agents on Base)
- [ ] ai16z/ElizaOS agent behavioral analysis
- [ ] Generic wallet-based scoring for non-registered agents (score any address, not just ERC-8004)

### Advanced Sybil Detection
- [ ] Temporal clustering — detect agents registered in coordinated time windows
- [ ] Funding source analysis — trace initial ETH to common faucets or mixers
- [ ] Behavioral fingerprinting — identical transaction patterns across wallets
- [ ] Machine learning classifier trained on confirmed sybil networks (84 networks = good training data)

### Trust Graph V2
- [ ] Weighted trust graph with edge scoring (interaction frequency, value, recency)
- [ ] Community detection algorithms (Louvain, Label Propagation) for organic cluster identification
- [ ] Interactive graph explorer in dashboard (currently static D3 visualization)
- [ ] Graph-based anomaly detection (sudden topology changes, bridge node emergence)

---

## Phase 3: DeFi Integration & Composability (Q4 2026)

*Make SentinelNet the trust layer that other protocols build on.*

### Trust-Gated DeFi
- [ ] Lending protocol integration — gate borrowing capacity by agent trust score
- [ ] Insurance protocol partnership — premium discounts for TRUST-rated agents
- [ ] DEX integration — warning overlays for swaps involving REJECT-rated agent tokens
- [ ] Yield aggregator filtering — exclude strategies managed by low-trust agents

### Composable Trust Primitives
- [ ] `TrustGateV2` contract with pluggable trust models (reputation, validation, hybrid)
- [ ] Solidity library for one-line trust checks (`require(SentinelNet.isTrusted(agentId))`)
- [ ] Trust score as ERC-20 soulbound token (non-transferable reputation NFT)
- [ ] Decay-aware on-chain scores — move exponential decay computation into contract logic

### Developer Platform
- [ ] Self-service trust policy builder (define custom trust thresholds, dimension weights, sybil tolerance)
- [ ] Embeddable trust badge widget (`<script>` tag for any website)
- [ ] Trust score webhooks with configurable filters (only notify on verdict changes, score drops > N points)
- [ ] Grafana dashboard template for Prometheus metrics

---

## Phase 4: Governance & Sustainability (Q1 2027)

*Transition from single-operator to community-governed infrastructure.*

### DAO Governance
- [ ] Community voting on scoring weights and verdict thresholds
- [ ] Dispute resolution council — elected validators review challenged scores
- [ ] Transparency reports (monthly ecosystem health, sybil trends, scoring accuracy)
- [ ] Open challenger pool — anyone can stake ETH to challenge published scores

### Economic Model
- [ ] Tiered API access (free: 100 req/hr, pro: 10K req/hr, enterprise: unlimited)
- [ ] Token-gated premium features (real-time webhooks, batch scoring, custom policies)
- [ ] Revenue share with active challengers (incentivize honest dispute participation)
- [ ] Grant funding for public goods (scoring is a positive externality for the ecosystem)

### Validation Registry Integration
- [ ] Activate when ERC-8004 team deploys the Validation Registry contract
- [ ] Implement SentinelNet as a validator — re-execute agent tasks and publish validation responses
- [ ] Support third-party validators querying SentinelNet scores as part of their validation logic
- [ ] Cross-reference validation results with reputation scores for stronger trust signals

---

## Phase 5: Intelligence Layer (Q2 2027)

*From scoring agents to understanding the agent ecosystem.*

### Predictive Analytics
- [ ] Trust trajectory forecasting — predict which agents will degrade before it happens
- [ ] Sybil network early warning — detect cluster formation in progress
- [ ] Ecosystem health index with trend analysis and alert thresholds
- [ ] Agent behavior change detection — flag sudden operational pattern shifts

### Agent-to-Agent Trust Protocol
- [ ] Mutual reputation — agents score each other, SentinelNet aggregates and verifies
- [ ] Trust negotiation — agents query SentinelNet before entering multi-party collaborations
- [ ] Reputation portability — export trust scores to other chains and protocols via attestations
- [ ] Trust inheritance — new agents deployed by trusted operators inherit a baseline score

### Research & Standards
- [ ] Publish scoring methodology paper (peer review, reproducibility)
- [ ] Contribute findings to ERC-8004 working group
- [ ] Open-source the scoring engine (keep infrastructure proprietary, open the algorithm)
- [ ] Benchmark against other agent reputation systems

---

## Design Principles

These principles guide every roadmap decision:

1. **Autonomy first.** SentinelNet operates without human intervention. Every new feature must work autonomously or not ship.

2. **On-chain verifiability.** Scores are backed by staked ETH, published to IPFS, and written on-chain. No trust-me claims.

3. **Composability over features.** Build primitives other protocols can use, not monolithic products.

4. **Real data, not simulations.** Every sybil network, every contagion penalty, every score is computed from real on-chain behavior. No synthetic benchmarks.

5. **Progressive decentralization.** Start as a single autonomous agent, evolve into community-governed infrastructure.

---

## How to Contribute

SentinelNet is open source: [github.com/Ridwannurudeen/sentinelnet](https://github.com/Ridwannurudeen/sentinelnet)

- **Report issues** — scoring errors, false positives, integration bugs
- **Challenge scores** — stake ETH and dispute a score you believe is wrong
- **Build integrations** — use the SDK, MCP tools, or TrustGate contract in your project
- **Run a validator** — when the Validation Registry goes live, validate agent behavior independently

---

*SentinelNet: Trust is earned on-chain, not claimed.*
