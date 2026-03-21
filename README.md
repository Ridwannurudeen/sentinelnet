# SentinelNet

**How do you trust something without a face?**

SentinelNet is an autonomous reputation watchdog for every ERC-8004 agent on Base. It runs 24/7 — discovering agents, analyzing their on-chain behavior across Base and Ethereum, computing 5-dimensional trust scores with sybil detection and trust decay, publishing verifiable evidence to IPFS, staking ETH behind every score, and writing composable reputation feedback on-chain. No human in the loop.

Other agents query SentinelNet before transacting with unknown counterparties. One MCP tool call. One trust score. Every score backed by on-chain proof, pinned evidence, and staked ETH.

## Live Right Now

SentinelNet is not a demo. It's running in production on Base Mainnet.

- **330+ agents scored** across all 3 verdict classes with active sybil detection
- **On-chain feedback** on the [ERC-8004 Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63)
- **IPFS evidence** pinned for every score (e.g. [ipfs://QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm](https://gateway.pinata.cloud/ipfs/QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm))
- **Staking contract** deployed at [`0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9`](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9) — ETH staked behind every published score
- **TrustGate contract** — composable on-chain trust oracle for other contracts to query
- **Agent ID 31253** registered on-chain via ERC-8004 Identity Registry
- **Live dashboard**: https://sentinelnet.gudman.xyz/dashboard
- **REST API**: https://sentinelnet.gudman.xyz/api/scores

## The Problem

35,000+ agents are registered on the ERC-8004 Identity Registry. Any agent can register. There's no built-in way to know which ones are trustworthy, which are Sybils, and which are interacting with malicious contracts. Agents transacting with unknown counterparties are flying blind.

## How It Works

SentinelNet runs a continuous autonomous loop:

```
Discover → Analyze → Score → Sybil Check → Stake → Publish → Repeat
```

```
┌──────────────────────────────────────────────────────────┐
│  SentinelNet Agent (autonomous loop)                     │
│                                                          │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Discovery │→ │ 5-Dimension  │→ │ Reputation     │    │
│  │ Sweep     │  │ Analyzer     │  │ Publisher      │    │
│  │ (30 min)  │  │ Pipeline     │  │ (on-chain +    │    │
│  │           │  │              │  │  IPFS + Stake) │    │
│  └───────────┘  └──────────────┘  └────────────────┘    │
│                                                          │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Sybil     │  │ Trust Decay  │  │ MCP + REST     │    │
│  │ Detector  │  │ Engine       │  │ Server (4      │    │
│  │ (-20 pts) │  │ (exp decay)  │  │  tools)        │    │
│  └───────────┘  └──────────────┘  └────────────────┘    │
└──────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ ERC-8004     │ │ ERC-8004     │ │ Staking +    │
  │ Identity     │ │ Reputation   │ │ TrustGate    │
  │ Registry     │ │ Registry     │ │ Contracts    │
  └──────────────┘ └──────────────┘ └──────────────┘
```

### The Decision Loop

1. **Discover** — Sweep the Identity Registry for new and unscored agents via `totalSupply()` and `ownerOf()`
2. **Analyze** — Fetch wallet history from Base + Ethereum, run 5 independent scoring dimensions
3. **Score** — Weighted aggregation with sybil penalties and trust decay
4. **Sybil Check** — Post-sweep cluster analysis flags coordinated agent rings (-20 point penalty)
5. **Stake** — Automatically stake ETH behind every published score via SentinelNetStaking contract
6. **Publish** — Pin evidence JSON to IPFS, write feedback to Reputation Registry
7. **Alert** — Emit on-chain `TrustDegraded` events when scores drop significantly
8. **Repeat** — Every 30 minutes, re-discover and re-score stale agents

## Scoring Model

Five analyzers run per agent, each measuring a different trust signal:

| Analyzer | Weight | What It Measures |
|----------|--------|-----------------|
| **Longevity** | 15% | Wallet age via logarithmic curve: `15 * ln(age + 1)` |
| **Activity** | 20% | Transaction volume (sqrt scaling), active day consistency, ETH balance |
| **Counterparty Quality** | 20% | Ratio of verified vs flagged interaction partners |
| **Contract Risk** | 20% | Malicious contract interactions, unverified contract ratio |
| **Agent Identity** | 25% | ERC-8004 metadata completeness, on-chain reputation count, wallet exclusivity |

The Agent Identity dimension is critical — it differentiates agents even when they share the same wallet address. An agent with rich ERC-8004 metadata, positive on-chain reputation, and an exclusive wallet scores higher than a bare registration sharing a wallet with 20 other agents.

### Verdicts

| Verdict | Score Range | Meaning |
|---------|-------------|---------|
| **TRUST** | >= 55 | Safe to interact with |
| **CAUTION** | 40-54 | Proceed with limits |
| **REJECT** | < 40 | Avoid this agent |

### Trust Decay

Scores decay exponentially over time: `effective_score = base_score * e^(-0.01 * days)`

After 30 days without re-scoring, a 90 becomes ~67. Decay is applied at query time — API and MCP responses always return the effective score with decay metadata. This forces continuous re-evaluation. Trust is not permanent.

### Sybil Detection

Cluster analysis runs after every sweep on the interaction graph. Groups of 3+ agents that only interact with each other get flagged and penalized (-20 points). Flagged agents are re-scored immediately with the sybil penalty applied. Sybil status is persisted and displayed on the dashboard.

## On-Chain Artifacts

Everything SentinelNet does leaves a trail on Base Mainnet:

| Artifact | Where | What |
|----------|-------|------|
| Agent identity | [Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) | Agent #31253 registered via ERC-8004 |
| Trust scores | [Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) | `giveFeedback()` with score + IPFS URI |
| Evidence | IPFS via Pinata | Full analysis JSON pinned per agent |
| Score stakes | [SentinelNetStaking](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9) | 0.001 ETH staked per score, 72h challenge window |
| Trust events | Staking contract | `ScoreStaked`, `StakeChallenged`, `TrustDegraded` events |
| Trust oracle | TrustGate contract | `isTrusted()`, `getTrustScore()` — composable on-chain queries |

## Smart Contracts

### SentinelNetStaking.sol

Deployed on Base Mainnet at [`0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9`](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9)

SentinelNet automatically stakes ETH on every score it publishes. The staking mechanism creates economic accountability:

- `stakeScore(agentId, score)` — stakes ETH backing the published score
- `challenge(stakeId)` — anyone can challenge within 72 hours
- `resolveChallenge(stakeId, result)` — resolution after investigation
- `emitTrustDegraded(agentId, prev, next)` — emits on-chain event when trust drops

### TrustGate.sol — Composable Trust Oracle

The killer feature for ecosystem integration. Other smart contracts on Base can query agent trust scores on-chain:

```solidity
import {TrustGate} from "sentinelnet/TrustGate.sol";

contract MyAgentMarketplace is TrustGate {
    function execute(uint256 agentId) external onlyTrusted(agentId) {
        // This only executes if the agent has a TRUST verdict
    }
}
```

Key functions:
- `isTrusted(agentId)` — returns bool, usable in any contract
- `getTrustScore(agentId)` — returns uint8 (0-100)
- `getTrustRecord(agentId)` — returns full record with evidence URI
- `getVerdict(agentId)` — returns "TRUST", "CAUTION", "REJECT", or "UNSCORED"
- `batchUpdateTrust(ids, scores, uris)` — batch score updates
- `onlyTrusted(agentId)` modifier — gate any function by trust status
- `onlyNotRejected(agentId)` modifier — allow TRUST + CAUTION, block REJECT

## MCP Integration

Any agent can query SentinelNet via Model Context Protocol. 4 tools available:

### `check_trust` — Score lookup with optional fresh analysis
```json
{
    "agent_id": 32263,
    "fresh": true
}
```
Response:
```json
{
    "agent_id": 32263,
    "trust_score": 70,
    "verdict": "TRUST",
    "longevity": 85,
    "activity": 68,
    "counterparty": 79,
    "contract_risk": 62,
    "agent_identity": 80,
    "evidence_uri": "ipfs://QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm",
    "decay_days": 2.5,
    "is_stale": false
}
```

### `list_scored_agents` — Browse all scored agents
Filter by verdict (TRUST/CAUTION/REJECT) with configurable limit.

### `get_ecosystem_stats` — Aggregate trust statistics
Total scored, average score, verdict breakdown, sybil count.

### `get_score_history` — Trust trends over time
Score history for any agent showing trust trajectory.

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with version |
| `/api/scores` | GET | All scored agents with decay, verdict breakdown, sybil count |
| `/api/stats` | GET | Aggregate statistics (avg, min, max, stale count) |
| `/trust/{agent_id}` | GET | Trust score with decay applied |
| `/trust/{agent_id}/history` | GET | Score history for trend analysis |
| `/trust/graph/{agent_id}` | GET | Agent's counterparty trust neighborhood |
| `/dashboard` | GET | Live monitoring dashboard |

## ERC-8004 Integration

SentinelNet is a first-class ERC-8004 participant:

- **Identity Registry** — Registered as Agent #31253 with full metadata
- **Reputation Registry** — Posts feedback entries per scored agent with IPFS evidence URIs
- **Validation Registry** — Ready to respond to `ValidationRequest` events with fresh analysis
- **tokenURI parsing** — Decodes base64 `data:application/json;base64,...` registration metadata
- **Wallet resolution** — `getAgentWallet()` with `ownerOf()` fallback

## Setup

```bash
git clone https://github.com/Ridwannurudeen/sentinelnet.git
cd sentinelnet
pip install -r requirements.txt
cp .env.example .env
# Fill in: BASE_RPC_URL, ETH_RPC_URL, PRIVATE_KEY, PINATA_JWT
```

## Run

```bash
# Start the API server + autonomous agent
python main.py
# Dashboard at http://localhost:8004/dashboard
```

## Tests

```bash
pytest tests/ -v
# 66 tests across 14 test files
```

## Project Structure

```
sentinelnet/
├── agent/
│   ├── __init__.py           # Agent orchestrator + staking + sybil wiring
│   ├── discovery.py          # Sweep loop + stale detection + post-sweep hooks
│   ├── trust_engine.py       # Weighted scoring + exponential decay
│   ├── sybil.py              # Sybil cluster detection (clique analysis)
│   ├── publisher.py          # IPFS + Reputation Registry + evidence builder
│   ├── validator.py          # Validation responder
│   ├── alerts.py             # Trust degradation detection
│   ├── graph.py              # Trust graph queries
│   ├── chain.py              # Base + Ethereum data fetcher
│   ├── erc8004.py            # ERC-8004 registry client
│   └── analyzers/
│       ├── longevity.py      # Logarithmic wallet age curve
│       ├── activity.py       # Sqrt tx volume + balance
│       ├── counterparty.py   # Verified vs flagged ratio
│       ├── contract_risk.py  # Malicious interaction scorer
│       └── agent_identity.py # Metadata + reputation + exclusivity
├── contracts/
│   ├── SentinelNetStaking.sol  # Deployed on Base Mainnet
│   └── TrustGate.sol           # Composable trust oracle
├── mcp/
│   └── server.py             # 4 MCP tools (check_trust, list, stats, history)
├── dashboard/
│   └── index.html            # Production monitoring dashboard
├── api.py                    # FastAPI REST server with decay + history
├── main.py                   # Entry point
├── db.py                     # SQLite WAL cache + score history
├── config.py                 # Pydantic Settings
└── tests/                    # 66 tests, 14 files
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+, asyncio |
| API | FastAPI, uvicorn |
| Smart Contracts | Solidity 0.8.24, Base Mainnet |
| Agent Protocol | MCP (Model Context Protocol) |
| Identity | ERC-8004 Identity + Reputation Registries |
| Storage | SQLite WAL (aiosqlite), IPFS (Pinata) |
| Chain Data | web3.py, Blockscout API |
| Analysis Chains | Base (registries + scoring), Ethereum (behavioral data) |

## Roadmap

Features planned for ecosystem integration:

- **Validation Registry listener** — Listen for `ValidationRequest` events and auto-respond
- **Multi-scorer aggregation** — Read reputation from other ERC-8004 reputation providers
- **EAS attestations** — Post scores as Ethereum Attestation Service attestations on Base
- **SDK** — `pip install sentinelnet` / `npm install @sentinelnet/sdk` for easy integration
- **Webhook subscriptions** — Other agents subscribe to trust change events
- **Cross-chain portability** — Trust on Base portable to other L2s
- **Dispute resolution** — Challenger stakes ETH, economic slashing on resolution
