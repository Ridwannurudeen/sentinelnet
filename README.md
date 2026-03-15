# SentinelNet

Autonomous agent reputation watchdog for ERC-8004 on Base. Discovers registered agents, analyzes their on-chain behavior across Base and Ethereum, publishes composable trust scores, and responds to validation requests.

Other agents query SentinelNet via MCP or REST before transacting with unknown counterparties.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  SentinelNet Agent (autonomous loop)                │
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Discovery │→ │ Analyzer  │→ │ Reputation     │  │
│  │ Sweep     │  │ Pipeline  │  │ Publisher      │  │
│  │ (30 min)  │  │ (4 scorers│  │ (on-chain)     │  │
│  └───────────┘  └───────────┘  └────────────────┘  │
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Event     │  │ Validator │  │ MCP + REST     │  │
│  │ Listener  │  │ Responder │  │ Server         │  │
│  └───────────┘  └───────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────┘
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ ERC-8004     │ │ ERC-8004     │ │ ERC-8004     │
│ Identity     │ │ Reputation   │ │ Validation   │
│ Registry     │ │ Registry     │ │ Registry     │
│ (Base)       │ │ (Base)       │ │ (Base)       │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Scoring Model

Four analyzers run in parallel per agent:

| Analyzer | Weight | What it measures |
|----------|--------|-----------------|
| Longevity | 0.20 | Wallet age, first transaction date |
| Activity | 0.25 | Transaction count, frequency, consistency |
| Counterparty Quality | 0.30 | Verified vs flagged interaction ratio |
| Contract Risk | 0.25 | Malicious contract interactions |

**Verdicts:**
- **TRUST** (>= 70): Safe to interact
- **CAUTION** (40-69): Proceed with limits
- **REJECT** (< 40): Avoid this agent

**Trust Decay:** `effective_score = base_score * e^(-0.01 * days)` — scores decay exponentially. After 30 days without re-scoring, a 90 becomes ~67.

**Sybil Detection:** Cluster analysis on the interaction graph. Groups of 3+ agents that only interact with each other get flagged and penalized (-20 points).

## Setup

```bash
git clone https://github.com/Ridwannurudeen/sentinelnet.git
cd sentinelnet
pip install -r requirements.txt
cp .env.example .env
# Fill in your RPC URLs, private key, and Pinata keys
```

## Run

```bash
# Start the API server + autonomous agent
uvicorn api:app --host 0.0.0.0 --port 8000

# Dashboard at http://localhost:8000/dashboard
```

## MCP Tool

```json
{
    "name": "check_trust",
    "description": "Check the trust score of an ERC-8004 registered agent.",
    "parameters": {
        "agent_id": "ERC-8004 agent ID (uint256)",
        "fresh": "Optional. If true, runs fresh analysis. Default false."
    }
}
```

Response:
```json
{
    "agent_id": 42,
    "trust_score": 73,
    "verdict": "TRUST",
    "breakdown": {
        "longevity": 85,
        "activity": 68,
        "counterparty_quality": 79,
        "contract_risk": 62
    },
    "decay_applied": false,
    "sybil_risk": false,
    "evidence_uri": "ipfs://..."
}
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/trust/{agent_id}` | GET | Get trust score for an agent |
| `/trust/graph/{agent_id}` | GET | Get agent's trust neighborhood |
| `/api/stats` | GET | Aggregate statistics |
| `/dashboard` | GET | Live monitoring dashboard |

## Smart Contract

**SentinelNetStaking.sol** on Base — SentinelNet stakes 0.001 ETH per score posted. 72-hour challenge window. Any address can challenge; if the agent was later mass-flagged, the challenger takes the stake.

## ERC-8004 Integration

- **Identity Registry:** Self-registers at startup (Agent ID: 31253)
- **Reputation Registry:** Posts 5 feedback entries per agent (composite + 4 sub-scores) with IPFS evidence
- **Validation Registry:** Monitors `ValidationRequest` events, runs full pipeline on demand

## Tests

```bash
pytest tests/ -v
# 51 tests across 11 test files
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
│       ├── longevity.py      # Wallet age scorer
│       ├── activity.py       # Tx frequency scorer
│       ├── counterparty.py   # Verified vs flagged ratio
│       └── contract_risk.py  # Malicious interaction scorer
├── contracts/
│   └── SentinelNetStaking.sol
├── mcp/
│   └── server.py             # check_trust MCP tool
├── dashboard/
│   └── index.html            # Live monitoring UI
├── api.py                    # FastAPI REST server
├── db.py                     # SQLite WAL cache
├── config.py                 # Pydantic Settings
└── tests/                    # 51 tests
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Contracts | Solidity 0.8.24, Hardhat, Base |
| MCP Server | Python MCP SDK |
| Database | SQLite WAL (aiosqlite) |
| IPFS | Pinata |
| Web3 | web3.py |
| Chains | Base (registries), Ethereum (analysis) |

## Features

1. Evidence on IPFS — pin analysis JSON, commit hash on-chain
2. Composable on-chain scores — Reputation Registry feedback entries
3. Self-registration — mint ERC-8004 identity at startup
4. Real-time events + sweep — event listener + 30-min sweep loop
5. MCP-native tool — check_trust for agent-to-agent use
6. Trust graph — counterparty data exposed via REST
7. Live dashboard — single HTML, auto-refresh
8. Trust decay — exponential decay on stale scores
9. Sybil detection — cluster analysis on interaction graph
10. Score staking — 0.001 ETH per score, challenge mechanism
11. Alert events — TrustDegraded on-chain event
12. Conversation log — raw brainstorm session submitted

## Hackathon

**The Synthesis 2026** — Agents that Trust

Prize Targets: Open Track ($14.5K), ERC-8004 ($4K), Let the Agent Cook ($4K)
