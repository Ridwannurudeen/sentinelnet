# SentinelNet

**How do you trust something without a face?**

SentinelNet is an autonomous reputation watchdog that answers this question for every ERC-8004 agent on Base. It runs 24/7 — discovering agents, analyzing their on-chain behavior across Base and Ethereum, computing 5-dimensional trust scores, publishing verifiable evidence to IPFS, and writing composable reputation feedback on-chain. No human in the loop.

Other agents query SentinelNet before transacting with unknown counterparties. One MCP tool call. One trust score. Every score backed by on-chain proof and pinned evidence.

## Live Right Now

SentinelNet is not a demo. It's running in production on Base Mainnet.

- **140+ agents scored** with 31 unique trust scores across all 3 verdict classes
- **On-chain feedback** on the [ERC-8004 Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63)
- **IPFS evidence** pinned for every score (e.g. [ipfs://QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm](https://gateway.pinata.cloud/ipfs/QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm))
- **Staking contract** deployed at [`0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9`](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9)
- **Agent ID 31253** registered on-chain via ERC-8004 Identity Registry
- **Live dashboard**: `http://75.119.153.252:8004/dashboard`
- **REST API**: `http://75.119.153.252:8004/api/scores`

## The Problem

35,000+ agents are registered on the ERC-8004 Identity Registry. Any agent can register. There's no built-in way to know which ones are trustworthy, which are Sybils, and which are interacting with malicious contracts. Agents transacting with unknown counterparties are flying blind.

## How It Works

SentinelNet runs a continuous autonomous loop:

```
Discover → Analyze → Score → Publish → Repeat
```

```
┌──────────────────────────────────────────────────────────┐
│  SentinelNet Agent (autonomous loop)                     │
│                                                          │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Discovery │→ │ 5-Dimension  │→ │ Reputation     │    │
│  │ Sweep     │  │ Analyzer     │  │ Publisher      │    │
│  │ (30 min)  │  │ Pipeline     │  │ (on-chain +    │    │
│  │           │  │              │  │  IPFS)         │    │
│  └───────────┘  └──────────────┘  └────────────────┘    │
│                                                          │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Sybil     │  │ Validator    │  │ MCP + REST     │    │
│  │ Detector  │  │ Responder    │  │ Server         │    │
│  └───────────┘  └──────────────┘  └────────────────┘    │
└──────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ ERC-8004     │ │ ERC-8004     │ │ Staking      │
  │ Identity     │ │ Reputation   │ │ Contract     │
  │ Registry     │ │ Registry     │ │ (Base)       │
  └──────────────┘ └──────────────┘ └──────────────┘
```

### The Decision Loop

1. **Discover** — Sweep the Identity Registry for new and unscored agents via `totalSupply()` and `ownerOf()`
2. **Analyze** — Fetch wallet history from Base + Ethereum, run 5 independent scoring dimensions
3. **Score** — Weighted aggregation with sybil penalties and trust decay
4. **Publish** — Pin evidence JSON to IPFS, write feedback to Reputation Registry, optionally stake ETH
5. **Repeat** — Every 30 minutes, re-discover and re-score stale agents

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

After 30 days without re-scoring, a 90 becomes ~67. This forces continuous re-evaluation — trust is not permanent.

### Sybil Detection

Cluster analysis on the interaction graph. Groups of 3+ agents that only interact with each other get flagged and penalized (-20 points).

## On-Chain Artifacts

Everything SentinelNet does leaves a trail on Base Mainnet:

| Artifact | Where | What |
|----------|-------|------|
| Agent identity | [Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) | Agent #31253 registered via ERC-8004 |
| Trust scores | [Reputation Registry](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) | `giveFeedback()` with score + IPFS URI |
| Evidence | IPFS via Pinata | Full analysis JSON pinned per agent |
| Score stakes | [SentinelNetStaking](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9) | 0.001 ETH staked per score, 72h challenge window |
| Trust events | Staking contract | `ScoreStaked`, `StakeChallenged`, `TrustDegraded` events |

## MCP Integration

Any agent can query SentinelNet via Model Context Protocol:

```json
{
    "name": "check_trust",
    "description": "Check the trust score of an ERC-8004 registered agent.",
    "inputSchema": {
        "properties": {
            "agent_id": { "type": "integer", "description": "ERC-8004 agent ID" },
            "fresh": { "type": "boolean", "description": "Run fresh analysis", "default": false }
        },
        "required": ["agent_id"]
    }
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
    "evidence_uri": "ipfs://QmPv5FzyH57KACzejXEd756yX1D2GebPumsgLboAFnm7jm"
}
```

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/scores` | GET | All scored agents with verdict breakdown |
| `/api/stats` | GET | Aggregate statistics |
| `/trust/{agent_id}` | GET | Trust score for a specific agent |
| `/trust/graph/{agent_id}` | GET | Agent's counterparty trust neighborhood |
| `/dashboard` | GET | Live monitoring dashboard |

## Smart Contract

**SentinelNetStaking.sol** — deployed on Base Mainnet at [`0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9`](https://basescan.org/address/0xE171554f0c5d71872663eE9f8a773db3Fe65d0B9)

SentinelNet stakes ETH on every score it publishes. The staking mechanism creates accountability:

- `stakeScore(agentId, score)` — stakes ETH backing the published score
- `challenge(stakeId)` — anyone can challenge within 72 hours
- `resolveChallenge(stakeId, result)` — resolution after investigation
- `emitTrustDegraded(agentId, prev, next)` — emits on-chain event when trust drops

## ERC-8004 Integration

SentinelNet is a first-class ERC-8004 participant:

- **Identity Registry** — Registered as Agent #31253 with full metadata
- **Reputation Registry** — Posts feedback entries per scored agent with IPFS evidence URIs
- **Validation Registry** — Monitors `ValidationRequest` events and responds with fresh analysis
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
# 56 tests across 14 test files
```

## Project Structure

```
sentinelnet/
├── agent/
│   ├── __init__.py           # Agent orchestrator
│   ├── discovery.py          # Sweep loop + stale detection
│   ├── trust_engine.py       # Weighted scoring + decay
│   ├── sybil.py              # Sybil cluster detection
│   ├── publisher.py          # IPFS + Reputation Registry
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
│   └── SentinelNetStaking.sol  # Deployed on Base Mainnet
├── mcp/
│   └── server.py             # check_trust MCP tool
├── dashboard/
│   └── index.html            # Live monitoring UI
├── api.py                    # FastAPI REST server
├── main.py                   # Entry point
├── db.py                     # SQLite WAL cache
├── config.py                 # Pydantic Settings
└── tests/                    # 56 tests, 14 files
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
