# SentinelNet

**The immune system for the ERC-8004 agent economy on Base.**

SentinelNet is an autonomous reputation watchdog that continuously discovers, analyzes, and scores every ERC-8004 agent on Base. It runs 24/7 with no human in the loop — scanning the full registry of 35,000+ agents, computing 5-dimensional trust scores, propagating trust contagion through interaction graphs, detecting sybil clusters, publishing verifiable evidence to IPFS, and writing composable reputation feedback on-chain.

Other agents query SentinelNet before transacting with unknown counterparties. One API call. One trust score. Every score backed by on-chain proof, pinned evidence, and staked ETH.

## Live Right Now

SentinelNet is not a demo. It's running in production on Base Mainnet.

- **480+ agents scored** across all 3 verdict classes, scanning all 35K+ registered agents
- **56 sybil agents flagged** across 8+ coordinated clusters (largest: 93 agents)
- **126 threat events** detected — sybil clusters, trust degradations, contagion events
- **On-chain feedback** on the [ERC-8004 Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63)
- **IPFS evidence** pinned for every score (e.g. [ipfs://QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm](https://gateway.pinata.cloud/ipfs/QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm))
- **Staking contract** at [`0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9`](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9)
- **Agent ID 31253** registered on-chain — [view live score](https://sentinelnet.gudman.xyz/trust/31253)
- **Live dashboard**: [sentinelnet.gudman.xyz/dashboard](https://sentinelnet.gudman.xyz/dashboard)
- **Trust Network Graph**: [sentinelnet.gudman.xyz/graph](https://sentinelnet.gudman.xyz/graph)
- **Threat Feed**: [sentinelnet.gudman.xyz/api/threats](https://sentinelnet.gudman.xyz/api/threats)

## The Problem

35,000+ agents are registered on the ERC-8004 Identity Registry. Any agent can register. There's no built-in way to know which ones are trustworthy, which are sybils, and which are interacting with malicious contracts. As the agent economy scales to millions of autonomous actors, it collapses into chaos without trust infrastructure.

SentinelNet is that infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  SentinelNet Agent (autonomous loop — no human in the loop)         │
│                                                                     │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │ Progressive│→ │ 5-Dimension  │→ │ Reputation    │               │
│  │ Discovery  │  │ Analyzer     │  │ Publisher     │               │
│  │ (full      │  │ Pipeline     │  │ (on-chain +   │               │
│  │  registry) │  │              │  │  IPFS + Stake)│               │
│  └────────────┘  └──────────────┘  └───────────────┘               │
│                                                                     │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │ Sybil      │  │ Trust        │  │ Threat        │               │
│  │ Detector   │  │ Contagion    │  │ Intelligence  │               │
│  │ (dual-     │  │ Engine       │  │ Feed          │               │
│  │  method)   │  │ (PageRank)   │  │ (real-time)   │               │
│  └────────────┘  └──────────────┘  └───────────────┘               │
│                                                                     │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │ Trust      │  │ EAS          │  │ MCP + REST +  │               │
│  │ Decay      │  │ Attestation  │  │ Python/JS SDK │               │
│  │ (exp)      │  │ (Base)       │  │ (5 tools)     │               │
│  └────────────┘  └──────────────┘  └───────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ ERC-8004     │ │ ERC-8004     │ │ Staking +    │
  │ Identity     │ │ Reputation   │ │ TrustGate    │
  │ Registry     │ │ Registry     │ │ Contracts    │
  └──────────────┘ └──────────────┘ └──────────────┘
```

### The Decision Loop

1. **Discover** — Progressive full-registry scan of all 35K+ agents in batches (cursor-based, wrapping)
2. **Analyze** — Fetch wallet history from Base + Ethereum, run 5 independent scoring dimensions
3. **Score** — Weighted aggregation with sybil penalties and trust decay
4. **Contagion** — PageRank-style trust propagation: interacting with bad agents drags your score down
5. **Sybil Check** — Dual-method detection: wallet-sharing clusters + interaction graph clique analysis
6. **Threat Record** — Log sybil clusters, trust degradations, and contagion events to threat feed
7. **Stake** — Automatically stake ETH behind every published score
8. **Publish** — Pin evidence JSON to IPFS, write feedback to Reputation Registry
9. **Alert** — Emit on-chain `TrustDegraded` events when scores drop significantly
10. **Repeat** — Every 30 minutes, score the next batch and rescore stale agents

## Scoring Model

Five analyzers run per agent, each measuring a different trust signal:

| Analyzer | Weight | What It Measures |
|----------|--------|-----------------|
| **Longevity** | 15% | Wallet age via logarithmic curve: `15 * ln(age + 1)` |
| **Activity** | 20% | Transaction volume (sqrt scaling), active day consistency, ETH balance |
| **Counterparty Quality** | 20% | Ratio of verified vs flagged interaction partners |
| **Contract Risk** | 20% | Malicious contract interactions, unverified contract ratio |
| **Agent Identity** | 25% | ERC-8004 metadata completeness, on-chain reputation from ALL clients, wallet exclusivity |

### Verdicts

| Verdict | Score Range | Meaning |
|---------|-------------|---------|
| **TRUST** | >= 55 | Safe to interact with |
| **CAUTION** | 40-54 | Proceed with limits |
| **REJECT** | < 40 | Avoid this agent |

### Trust Contagion

PageRank-style recursive trust propagation through the agent interaction graph. If you regularly transact with REJECT agents, your score gets dragged down. If you interact with high-trust agents, you get a boost.

- Negative contagion weight: 0.6 (bad actors spread distrust faster)
- Positive contagion weight: 0.2
- Damping factor: 0.3
- Adjustments capped: -15 to +10

### Sybil Detection

Dual-method detection catches coordinated agent rings:

1. **Wallet-sharing** — 3+ agents registered on the same wallet = sybil cluster
2. **Interaction graph** — Clique detection finds groups that only interact with each other

Flagged agents get -20 point penalty and are immediately re-scored. Clusters are logged to the threat intelligence feed.

**Real results**: Found 8+ sybil clusters including a 93-agent cluster, a 55-agent cluster, and a 52-agent cluster — all sharing the same wallet address.

### Trust Decay

Scores decay exponentially: `effective_score = base_score * e^(-0.01 * days)`

After 30 days without re-scoring, a 90 becomes ~67. Decay is applied at query time. Trust is not permanent.

## Integration

### Python SDK

```bash
pip install sentinelnet
```

```python
from sentinelnet import SentinelNet

sn = SentinelNet()

# Get trust score
score = sn.get_trust(31253)
print(f"Score: {score['trust_score']}, Verdict: {score['verdict']}")

# Gate an interaction — only proceed if agent is trustworthy
if sn.trust_gate(agent_id=42, min_score=55):
    execute_transaction()

# Batch query 100 agents at once
results = sn.batch_trust([1, 2, 3, 100, 200])

# Async support
from sentinelnet import AsyncSentinelNet
async with AsyncSentinelNet() as sn:
    score = await sn.get_trust(31253)
```

### JavaScript SDK

```bash
npm install sentinelnet
```

```javascript
import SentinelNet from "sentinelnet";

const sn = new SentinelNet();

// Get trust score
const score = await sn.getTrust(31253);
console.log(`Verdict: ${score.verdict}`);

// Gate an interaction
if (await sn.trustGate(42, 55)) {
  executeTransaction();
}

// Threat intelligence
const threats = await sn.getThreats(10);
```

Full TypeScript types included.

### Smart Contracts

**TrustGate.sol** — Composable on-chain trust oracle:

```solidity
import {TrustGate} from "sentinelnet/TrustGate.sol";

contract MyAgentMarketplace is TrustGate {
    function execute(uint256 agentId) external onlyTrusted(agentId) {
        // Only executes if agent has TRUST verdict
    }
}
```

Functions: `isTrusted()`, `getTrustScore()`, `getVerdict()`, `getTrustRecord()`, `batchUpdateTrust()`
Modifiers: `onlyTrusted()`, `onlyNotRejected()`

### MCP Integration

5 tools via Model Context Protocol for agent-to-agent trust queries:

| Tool | Description |
|------|-------------|
| `check_trust` | Score lookup with optional fresh on-chain analysis |
| `list_scored_agents` | Browse all scored agents, filter by verdict |
| `get_ecosystem_stats` | Aggregate trust statistics |
| `get_score_history` | Trust trends over time |
| `get_threat_feed` | Real-time threat intelligence feed |

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trust/{agent_id}` | GET | Trust score with decay + explanation |
| `/trust/{agent_id}/history` | GET | Score history for trend analysis |
| `/trust/batch` | POST | Batch query up to 100 agents |
| `/trust/graph/{agent_id}` | GET | Counterparty trust neighborhood |
| `/badge/{agent_id}.svg` | GET | Embeddable SVG trust badge |
| `/api/scores` | GET | All scored agents with verdicts |
| `/api/stats` | GET | Ecosystem statistics |
| `/api/threats` | GET | Real-time threat intelligence feed |
| `/api/graph-data` | GET | Full interaction graph for visualization |
| `/api/score/{agent_id}` | POST | Trigger on-demand scoring |
| `/api/health` | GET | Health check |

Interactive API docs at [/docs](https://sentinelnet.gudman.xyz/docs).

## Threat Intelligence

Real-time feed of ecosystem threats detected autonomously:

| Threat Type | Severity | Description |
|-------------|----------|-------------|
| `SYBIL_CLUSTER` | HIGH | Coordinated cluster of agents sharing wallets or forming closed loops |
| `TRUST_DEGRADED` | HIGH | Agent's trust score dropped significantly between rescores |
| `TRUST_CONTAGION` | MEDIUM | Agent's score penalized due to interactions with low-trust neighbors |

## On-Chain Artifacts

| Artifact | Where | What |
|----------|-------|------|
| Agent identity | [Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) | Agent #31253 registered via ERC-8004 |
| Trust scores | [Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) | `giveFeedback()` per agent with IPFS URI |
| Evidence | IPFS via Pinata | Full analysis JSON pinned per agent |
| Score stakes | [SentinelNetStaking](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9) | ETH staked per score, 72h challenge window |
| Trust oracle | TrustGate contract | `isTrusted()`, `getTrustScore()` — composable queries |

## Setup

```bash
git clone https://github.com/Ridwannurudeen/sentinelnet.git
cd sentinelnet
pip install -r requirements.txt
cp .env.example .env
# Fill in: BASE_RPC_URL, ETH_RPC_URL, PRIVATE_KEY, PINATA_JWT
python main.py
# Dashboard at http://localhost:8004/dashboard
```

## Tests

```bash
pytest tests/ -v
# 83 tests across 16 test files
```

## Project Structure

```
sentinelnet/
├── agent/
│   ├── __init__.py           # Agent orchestrator + staking + contagion + sybil wiring
│   ├── discovery.py          # Progressive full-registry sweep (cursor-based batches)
│   ├── trust_engine.py       # Weighted scoring + exponential decay
│   ├── contagion.py          # PageRank-style trust propagation engine
│   ├── sybil.py              # Dual-method sybil detection (wallet-sharing + cliques)
│   ├── eas.py                # EAS attestation integration for Base
│   ├── publisher.py          # IPFS + Reputation Registry + evidence builder
│   ├── validator.py          # Validation responder
│   ├── alerts.py             # Trust degradation detection
│   ├── graph.py              # Trust graph queries
│   ├── chain.py              # Base + Ethereum data fetcher
│   ├── erc8004.py            # ERC-8004 registry client (getClients + getSummary)
│   └── analyzers/
│       ├── longevity.py      # Logarithmic wallet age curve
│       ├── activity.py       # Sqrt tx volume + balance
│       ├── counterparty.py   # Verified vs flagged ratio
│       ├── contract_risk.py  # Malicious interaction scorer
│       └── agent_identity.py # Metadata + reputation + exclusivity
├── contracts/
│   ├── SentinelNetStaking.sol  # Deployed on Base Mainnet
│   └── TrustGate.sol           # Composable trust oracle
├── sdk/
│   ├── python/               # pip install sentinelnet (sync + async)
│   └── js/                   # npm install sentinelnet (TypeScript types)
├── mcp/
│   └── server.py             # 5 MCP tools
├── dashboard/
│   ├── landing.html          # Landing page
│   ├── index.html            # Live monitoring dashboard with threat ticker
│   ├── agent.html            # Agent profile pages
│   ├── graph.html            # D3.js interactive trust network visualization
│   └── docs.html             # Integration guide
├── api.py                    # FastAPI REST server (11 endpoints)
├── main.py                   # Entry point + self-score on startup
├── db.py                     # SQLite WAL cache + score history + threats
├── config.py                 # Pydantic Settings
└── tests/                    # 83 tests, 16 files
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+, asyncio |
| API | FastAPI, uvicorn |
| Smart Contracts | Solidity 0.8.24, Base Mainnet |
| Agent Protocol | MCP (Model Context Protocol) |
| Identity | ERC-8004 Identity + Reputation Registries |
| Attestations | EAS (Ethereum Attestation Service) on Base |
| Storage | SQLite WAL (aiosqlite), IPFS (Pinata) |
| Chain Data | web3.py, Blockscout API |
| Visualization | D3.js force-directed graph |
| SDKs | Python (httpx), JavaScript (fetch, TypeScript) |
| Analysis Chains | Base (registries + scoring), Ethereum (behavioral data) |
