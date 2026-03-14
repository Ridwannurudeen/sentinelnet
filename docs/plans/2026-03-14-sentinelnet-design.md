# SentinelNet — Autonomous Agent Reputation Watchdog

## Overview

SentinelNet is an autonomous agent that discovers other agents on the ERC-8004 Identity Registry (Base Mainnet), analyzes their on-chain behavior across Base and Ethereum, posts composable trust scores to the Reputation Registry, and responds to validation requests. Other agents query SentinelNet via MCP or REST before transacting with unknown counterparties.

**Hackathon:** The Synthesis 2026 (synthesis.md)
**Theme:** Agents that Trust
**Prize Targets:** Open Track ($14.5K), ERC-8004 ($4K), Let the Agent Cook ($4K)

---

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

### Components

1. **Discovery Sweep** — Polls Identity Registry every 30 minutes for new agent registrations. Also listens for real-time `Registered` events to score new agents within seconds.

2. **Analyzer Pipeline** — Four scorers run in parallel:
   - Longevity (0.20) — wallet age, first tx date
   - Activity (0.25) — tx count, frequency, consistency
   - Counterparty Quality (0.30) — verified vs flagged interaction ratio
   - Contract Risk (0.25) — malicious contract interactions

3. **Reputation Publisher** — Posts 5 feedback entries per agent to the Reputation Registry (composite + 4 sub-scores). Pins full analysis JSON to IPFS for verifiable evidence.

4. **Validator Responder** — Watches for `ValidationRequest` events targeting SentinelNet. Runs full pipeline on demand and posts response.

5. **Event Listener** — Real-time listener for `Registered` and `ValidationRequest` events on the Identity and Validation registries.

6. **MCP + REST Server** — `check_trust(agent_id)` MCP tool + `GET /trust/{agent_id}` REST endpoint.

---

## Data Flow

```
New agent registered on ERC-8004
        │
        ▼
Discovery (sweep or real-time event)
        │
        ▼
Analyzer Pipeline (parallel)
  ├─ Longevity:          wallet age, first tx      → 0-100
  ├─ Activity:           tx count, frequency       → 0-100
  ├─ Counterparty:       verified vs flagged ratio → 0-100
  └─ Contract Risk:      malicious interactions    → 0-100
        │
        ▼
Weighted composite TrustScore (0-100)
  Longevity         × 0.20
  Activity          × 0.25
  Counterparty      × 0.30  (heaviest — hardest to fake)
  Contract Risk     × 0.25
        │
        ├─→ Trust Decay applied (exponential, based on score age)
        ├─→ Sybil Detection (cluster analysis on interaction graph)
        ├─→ Alert check (>20pt drop → TrustDegraded event)
        │
        ▼
Reputation Publisher
  → Pin analysis JSON to IPFS
  → Post 5 feedback entries to Reputation Registry
  → Stake 0.001 ETH on the score (SentinelNetStaking contract)
        │
        ▼
SQLite cache + trust graph edges updated
```

---

## Scoring Model

### Verdicts

| Verdict | Score | Meaning |
|---------|-------|---------|
| TRUST | >= 70 | Safe to interact |
| CAUTION | 40-69 | Proceed with limits |
| REJECT | < 40 | Avoid this agent |

### Trust Decay

Scores decay exponentially over time:
- `effective_score = base_score × e^(-λt)` where t = days since last scored, λ = 0.01
- A score of 90 after 30 days of no re-scoring → ~74
- Agents with decayed scores get a `stale: true` flag in responses
- Re-scoring resets the decay timer

### Sybil Detection

The counterparty analyzer builds interaction edges. Sybil detection flags clusters where:
- N agents (N >= 3) only interact with each other
- Minimal or zero interactions outside the cluster
- Flagged agents get a `sybil_risk: true` flag and a score penalty (-20)

---

## ERC-8004 Integration

### Self-Registration (Identity Registry)
- Mints ERC-8004 NFT at startup
- Registration file: MCP + REST endpoints in `services[]`
- `supportedTrust: ["reputation"]`

### Posting Reputation (Reputation Registry)
- `giveFeedback(agentId, value, 0, tag1, tag2, endpoint, feedbackURI, feedbackHash)`
- `tag1` = score type: `trustScore`, `longevity`, `activity`, `counterparty`, `contractRisk`
- `tag2` = `sentinelnet-v1`
- `feedbackURI` = IPFS CID of full analysis JSON
- Posts all 5 scores per agent per cycle

### Validation Responses (Validation Registry)
- Monitors `ValidationRequest` events where `validatorAddress` = SentinelNet
- Runs full pipeline, posts `validationResponse(requestHash, score, responseURI, responseHash, "trust-assessment")`

---

## Score Staking

Smart contract: `SentinelNetStaking.sol` on Base

- SentinelNet stakes 0.001 ETH per score posted
- Challenge window: 72 hours
- Any address can challenge a score by providing evidence (the agent was later mass-flagged)
- If challenge succeeds: stake goes to challenger
- If challenge fails or expires: stake returns to SentinelNet

This gives SentinelNet skin in the game. The agent literally bets money on its judgment.

---

## Alert Events

On-chain event emitted when trust degrades:

```solidity
event TrustDegraded(uint256 indexed agentId, uint8 previousScore, uint8 newScore, uint256 timestamp);
```

Trigger: score drops > 20 points between evaluations. Any agent can subscribe to these events and automatically stop interacting with degraded counterparties.

---

## MCP Tool Interface

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
    "wallet": "0x...",
    "chains_analyzed": ["base", "ethereum"],
    "scored_at": "2026-03-15T12:00:00Z",
    "on_chain_feedback_tx": "0x...",
    "evidence_uri": "ipfs://...",
    "stake_tx": "0x..."
}
```

REST: `GET /trust/{agent_id}` returns identical response.

---

## Live Dashboard

Single HTML file at `/dashboard`. Shows:
- Agents discovered count
- Latest trust scores posted (real-time feed)
- Validation requests answered
- Sybil clusters detected
- Sweep status + next sweep countdown
- Trust degradation alerts

Auto-refreshes every 15 seconds. Same pattern as ShieldBot's dashboard.

---

## Project Structure

```
sentinelnet/
├── contracts/
│   ├── SentinelNetStaking.sol    # Score staking + challenge
│   └── hardhat.config.js
│
├── agent/
│   ├── __init__.py               # Agent orchestrator
│   ├── discovery.py              # Sweep loop + event listener
│   ├── analyzers/
│   │   ├── longevity.py          # Wallet age scorer
│   │   ├── activity.py           # Tx frequency scorer
│   │   ├── counterparty.py       # Verified vs flagged ratio
│   │   └── contract_risk.py      # Malicious interaction scorer
│   ├── trust_engine.py           # Weighted composite + decay
│   ├── sybil.py                  # Sybil cluster detection
│   ├── publisher.py              # Reputation Registry + IPFS
│   ├── staker.py                 # Score staking interactions
│   ├── validator.py              # Validation Registry responder
│   ├── alerts.py                 # TrustDegraded event emitter
│   └── graph.py                  # Trust graph edges
│
├── mcp/
│   └── server.py                 # check_trust MCP tool
│
├── dashboard/
│   └── index.html                # Live dashboard
│
├── api.py                        # FastAPI (REST + dashboard)
├── db.py                         # SQLite WAL cache
├── config.py                     # Pydantic Settings
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Contracts | Solidity, Hardhat, Base Mainnet |
| MCP Server | Python MCP SDK |
| Database | SQLite WAL (aiosqlite) |
| IPFS | Pinata or web3.storage |
| Web3 | web3.py (Base + Ethereum RPCs) |
| Settings | Pydantic Settings |

---

## Chains

| Chain | Purpose |
|-------|---------|
| Base | ERC-8004 registries, staking contract, on-chain scores |
| Ethereum | Agent wallet behavioral analysis (deeper history) |

---

## 12 Features Summary

| # | Feature | Implementation |
|---|---------|---------------|
| 1 | Evidence on IPFS | Pin analysis JSON, commit hash on-chain |
| 2 | Composable on-chain scores | Reputation Registry feedback entries |
| 3 | Self-registration | Mint ERC-8004 identity at startup |
| 4 | Real-time events + sweep | Event listener + 30-min sweep loop |
| 5 | MCP-native tool | check_trust tool for agent-to-agent use |
| 6 | Trust graph edges | Counterparty data exposed via REST |
| 7 | Live dashboard | Single HTML, auto-refresh |
| 8 | Trust decay | Exponential decay on stale scores |
| 9 | Sybil detection | Cluster analysis on interaction graph |
| 10 | Score staking | 0.001 ETH per score, challenge mechanism |
| 11 | Alert events | TrustDegraded on-chain event |
| 12 | Conversation log | Raw brainstorm session submitted |
