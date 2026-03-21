# SentinelNet JavaScript SDK

Trust scoring for ERC-8004 agents on Base.

## Install

```bash
npm install sentinelnet
```

## Quick Start

```javascript
import SentinelNet from "sentinelnet";

const sn = new SentinelNet();

// Get trust score
const score = await sn.getTrust(31253);
console.log(`Score: ${score.trust_score}, Verdict: ${score.verdict}`);

// Gate an interaction
if (await sn.trustGate(42, 55)) {
  console.log("Agent is safe to interact with");
}

// Batch query
const results = await sn.batchTrust([1, 2, 3, 100, 200]);

// Threat intelligence
const threats = await sn.getThreats(10);
```

## CommonJS

```javascript
const SentinelNet = require("sentinelnet");
const sn = new SentinelNet();
```

## API Reference

| Method | Description |
|--------|-------------|
| `getTrust(agentId)` | Get full trust score with explanation |
| `isTrusted(agentId)` | Quick boolean trust check |
| `trustGate(agentId, minScore)` | Gate interactions by minimum score |
| `batchTrust(agentIds)` | Query up to 100 agents at once |
| `getHistory(agentId)` | Score history over time |
| `getGraph(agentId)` | Counterparty neighborhood |
| `getThreats(limit)` | Real-time threat intelligence feed |
| `getStats()` | Ecosystem-wide statistics |
| `badgeUrl(agentId)` | Embeddable SVG badge URL |

## Self-Hosted

```javascript
const sn = new SentinelNet({ baseUrl: "http://localhost:8004" });
```

## TypeScript

Full type definitions included (`src/index.d.ts`).
