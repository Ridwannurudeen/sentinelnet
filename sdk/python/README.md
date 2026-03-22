# SentinelNet Python SDK

Trust scoring for ERC-8004 agents on Base.

## Install

```bash
pip install sentinelnet
```

Or from source:

```bash
pip install git+https://github.com/Ridwannurudeen/sentinelnet.git#subdirectory=sdk/python
```

## Quick Start

```python
from sentinelnet import SentinelNet

sn = SentinelNet()

# Get trust score
score = sn.get_trust(31253)
print(f"Score: {score['trust_score']}, Verdict: {score['verdict']}")

# Gate an interaction
if sn.trust_gate(agent_id=42, min_score=55):
    print("Agent is safe to interact with")

# Batch query
results = sn.batch_trust([1, 2, 3, 100, 200])

# Threat intelligence
threats = sn.get_threats(limit=10)
```

## Async Usage

```python
from sentinelnet import AsyncSentinelNet

async with AsyncSentinelNet() as sn:
    score = await sn.get_trust(31253)
    trusted = await sn.is_trusted(42)
```

## API Reference

| Method | Description |
|--------|-------------|
| `get_trust(agent_id)` | Get full trust score with explanation |
| `is_trusted(agent_id)` | Quick boolean trust check |
| `trust_gate(agent_id, min_score)` | Gate interactions by minimum score |
| `batch_trust(agent_ids)` | Query up to 100 agents at once |
| `get_history(agent_id)` | Score history over time |
| `get_graph(agent_id)` | Counterparty neighborhood |
| `get_threats(limit)` | Real-time threat intelligence feed |
| `get_stats()` | Ecosystem-wide statistics |
| `badge_url(agent_id)` | Embeddable SVG badge URL |

## Self-Hosted

```python
sn = SentinelNet(base_url="http://localhost:8004")
```
