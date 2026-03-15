# SentinelNet Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an autonomous agent reputation watchdog that discovers ERC-8004 agents, scores their on-chain behavior, and publishes composable trust scores.

**Architecture:** Python FastAPI backend with 4 parallel analyzers feeding a weighted trust engine. Scores published to ERC-8004 Reputation Registry on Base. MCP server exposes `check_trust` tool. SQLite WAL cache. SentinelNetStaking.sol for skin-in-the-game scoring.

**Tech Stack:** Python 3.11+, FastAPI, web3.py, aiosqlite, Hardhat, Solidity, MCP Python SDK, Pinata (IPFS)

**Key Addresses (Base Mainnet):**
- Identity Registry: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- SentinelNet Agent ID: `31253`
- Owner: `0x6FFa1e00509d8B625c2F061D7dB07893B37199BC`
- Reputation Registry: discover via ERC-8004 docs or on-chain
- Validation Registry: discover via ERC-8004 docs or on-chain

**Timeline:** 8 days (Mar 15–22, 2026)

---

## Task 1: Project Scaffolding + Config

**Files:**
- Create: `config.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Test: `tests/test_config.py`

**Step 1: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
venv/
*.db
node_modules/
artifacts/
cache/
.pytest_cache/
```

**Step 2: Write `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.0
web3==6.15.1
aiosqlite==0.20.0
pydantic-settings==2.4.0
httpx==0.27.0
python-dotenv==1.0.1
mcp==1.0.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

**Step 3: Write `.env.example`**

```env
# RPC
BASE_RPC_URL=https://mainnet.base.org
ETH_RPC_URL=https://eth.llamarpc.com

# ERC-8004 (Base Mainnet)
IDENTITY_REGISTRY=0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
REPUTATION_REGISTRY=
VALIDATION_REGISTRY=
SENTINELNET_AGENT_ID=31253

# Wallet (for on-chain transactions)
PRIVATE_KEY=

# IPFS
PINATA_API_KEY=
PINATA_SECRET_KEY=

# Staking
STAKE_AMOUNT_ETH=0.001

# Sweep
SWEEP_INTERVAL_SECONDS=1800
RESCORE_AFTER_HOURS=24
```

**Step 4: Write the failing test**

```python
# tests/test_config.py
from config import Settings

def test_settings_defaults():
    s = Settings(
        BASE_RPC_URL="https://mainnet.base.org",
        ETH_RPC_URL="https://eth.llamarpc.com",
        IDENTITY_REGISTRY="0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        SENTINELNET_AGENT_ID=31253,
        PRIVATE_KEY="0x" + "ab" * 32,
    )
    assert s.SWEEP_INTERVAL_SECONDS == 1800
    assert s.STAKE_AMOUNT_ETH == 0.001
    assert s.RESCORE_AFTER_HOURS == 24

def test_settings_requires_base_rpc():
    import pytest
    with pytest.raises(Exception):
        Settings()
```

**Step 5: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

**Step 6: Write minimal implementation**

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RPC
    BASE_RPC_URL: str
    ETH_RPC_URL: str = "https://eth.llamarpc.com"

    # ERC-8004
    IDENTITY_REGISTRY: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    REPUTATION_REGISTRY: str = ""
    VALIDATION_REGISTRY: str = ""
    SENTINELNET_AGENT_ID: int = 31253

    # Wallet
    PRIVATE_KEY: str = ""

    # IPFS
    PINATA_API_KEY: str = ""
    PINATA_SECRET_KEY: str = ""

    # Staking
    STAKE_AMOUNT_ETH: float = 0.001

    # Sweep
    SWEEP_INTERVAL_SECONDS: int = 1800
    RESCORE_AFTER_HOURS: int = 24

    class Config:
        env_file = ".env"
```

**Step 7: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 tests)

**Step 8: Commit**

```bash
git add .gitignore requirements.txt .env.example config.py tests/test_config.py
git commit -m "feat: project scaffolding — config, requirements, env"
```

---

## Task 2: Database Layer

**Files:**
- Create: `db.py`
- Test: `tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py
import pytest
import asyncio
from db import Database

@pytest.fixture
def db():
    d = Database(":memory:")
    asyncio.get_event_loop().run_until_complete(d.init())
    yield d
    asyncio.get_event_loop().run_until_complete(d.close())

def test_save_and_get_trust_score(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_score(
            agent_id=42,
            wallet="0xabc",
            trust_score=73,
            longevity=85,
            activity=68,
            counterparty=79,
            contract_risk=62,
            verdict="TRUST",
            feedback_tx="0xtx1",
            evidence_uri="ipfs://abc",
        )
    )
    score = asyncio.get_event_loop().run_until_complete(db.get_score(42))
    assert score["trust_score"] == 73
    assert score["verdict"] == "TRUST"
    assert score["longevity"] == 85

def test_get_score_returns_none_for_unknown(db):
    score = asyncio.get_event_loop().run_until_complete(db.get_score(999))
    assert score is None

def test_save_graph_edge(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_edge(agent_id=42, counterparty="0xdef", interaction_count=5, is_flagged=False)
    )
    edges = asyncio.get_event_loop().run_until_complete(db.get_edges(42))
    assert len(edges) == 1
    assert edges[0]["counterparty"] == "0xdef"

def test_get_all_scores(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "0x1", "ipfs://1")
    )
    asyncio.get_event_loop().run_until_complete(
        db.save_score(2, "0xb", 30, 30, 30, 30, 30, "REJECT", "0x2", "ipfs://2")
    )
    all_scores = asyncio.get_event_loop().run_until_complete(db.get_all_scores())
    assert len(all_scores) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# db.py
import aiosqlite
from datetime import datetime, timezone

class Database:
    def __init__(self, path: str = "sentinelnet.db"):
        self.path = path
        self.conn = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trust_scores (
                agent_id INTEGER PRIMARY KEY,
                wallet TEXT NOT NULL,
                trust_score INTEGER NOT NULL,
                longevity INTEGER NOT NULL,
                activity INTEGER NOT NULL,
                counterparty INTEGER NOT NULL,
                contract_risk INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                feedback_tx TEXT,
                evidence_uri TEXT,
                scored_at TEXT NOT NULL
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                counterparty TEXT NOT NULL,
                interaction_count INTEGER DEFAULT 0,
                is_flagged BOOLEAN DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(agent_id, counterparty)
            )
        """)
        await self.conn.commit()

    async def save_score(self, agent_id, wallet, trust_score, longevity,
                         activity, counterparty, contract_risk, verdict,
                         feedback_tx, evidence_uri):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT OR REPLACE INTO trust_scores
            (agent_id, wallet, trust_score, longevity, activity, counterparty,
             contract_risk, verdict, feedback_tx, evidence_uri, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, wallet, trust_score, longevity, activity, counterparty,
              contract_risk, verdict, feedback_tx, evidence_uri, now))
        await self.conn.commit()

    async def get_score(self, agent_id):
        cursor = await self.conn.execute(
            "SELECT * FROM trust_scores WHERE agent_id = ?", (agent_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_scores(self):
        cursor = await self.conn.execute("SELECT * FROM trust_scores ORDER BY scored_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def save_edge(self, agent_id, counterparty, interaction_count, is_flagged):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT OR REPLACE INTO graph_edges
            (agent_id, counterparty, interaction_count, is_flagged, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, counterparty, interaction_count, is_flagged, now))
        await self.conn.commit()

    async def get_edges(self, agent_id):
        cursor = await self.conn.execute(
            "SELECT * FROM graph_edges WHERE agent_id = ?", (agent_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def close(self):
        if self.conn:
            await self.conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite WAL database — trust scores + graph edges"
```

---

## Task 3: Trust Engine (Weighted Scoring + Decay)

**Files:**
- Create: `agent/trust_engine.py`
- Create: `agent/__init__.py`
- Create: `agent/analyzers/__init__.py`
- Test: `tests/test_trust_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_trust_engine.py
from agent.trust_engine import TrustEngine, TrustResult

def test_compute_trust_score():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60)
    # 80*0.20 + 70*0.25 + 90*0.30 + 60*0.25 = 16 + 17.5 + 27 + 15 = 75.5 → 76
    assert result.trust_score == 76
    assert result.verdict == "TRUST"

def test_verdict_caution():
    engine = TrustEngine()
    result = engine.compute(longevity=50, activity=40, counterparty=50, contract_risk=40)
    # 50*0.20 + 40*0.25 + 50*0.30 + 40*0.25 = 10 + 10 + 15 + 10 = 45
    assert result.verdict == "CAUTION"

def test_verdict_reject():
    engine = TrustEngine()
    result = engine.compute(longevity=20, activity=10, counterparty=30, contract_risk=10)
    # 20*0.20 + 10*0.25 + 30*0.30 + 10*0.25 = 4 + 2.5 + 9 + 2.5 = 18
    assert result.verdict == "REJECT"

def test_decay_recent_score_unchanged():
    engine = TrustEngine()
    effective = engine.apply_decay(base_score=90, days_since_scored=0)
    assert effective == 90

def test_decay_30_days():
    engine = TrustEngine()
    effective = engine.apply_decay(base_score=90, days_since_scored=30)
    # 90 * e^(-0.01*30) = 90 * 0.7408 ≈ 67
    assert 65 <= effective <= 69

def test_decay_stale_flag():
    engine = TrustEngine()
    assert engine.is_stale(days_since_scored=0) is False
    assert engine.is_stale(days_since_scored=7) is True

def test_sybil_penalty():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60, sybil_risk=True)
    # 76 - 20 = 56
    assert result.trust_score == 56
    assert result.sybil_risk is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trust_engine.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/__init__.py
# SentinelNet Agent
```

```python
# agent/analyzers/__init__.py
# Analyzer plugins
```

```python
# agent/trust_engine.py
import math
from dataclasses import dataclass

WEIGHTS = {
    "longevity": 0.20,
    "activity": 0.25,
    "counterparty": 0.30,
    "contract_risk": 0.25,
}

DECAY_LAMBDA = 0.01
STALE_THRESHOLD_DAYS = 7
SYBIL_PENALTY = 20

@dataclass
class TrustResult:
    trust_score: int
    verdict: str
    longevity: int
    activity: int
    counterparty: int
    contract_risk: int
    sybil_risk: bool = False
    decay_applied: bool = False

class TrustEngine:
    def compute(self, longevity: int, activity: int, counterparty: int,
                contract_risk: int, sybil_risk: bool = False) -> TrustResult:
        raw = (
            longevity * WEIGHTS["longevity"]
            + activity * WEIGHTS["activity"]
            + counterparty * WEIGHTS["counterparty"]
            + contract_risk * WEIGHTS["contract_risk"]
        )
        score = round(raw)
        if sybil_risk:
            score = max(0, score - SYBIL_PENALTY)
        verdict = self._verdict(score)
        return TrustResult(
            trust_score=score,
            verdict=verdict,
            longevity=longevity,
            activity=activity,
            counterparty=counterparty,
            contract_risk=contract_risk,
            sybil_risk=sybil_risk,
        )

    def apply_decay(self, base_score: int, days_since_scored: float) -> int:
        decayed = base_score * math.exp(-DECAY_LAMBDA * days_since_scored)
        return round(decayed)

    def is_stale(self, days_since_scored: float) -> bool:
        return days_since_scored >= STALE_THRESHOLD_DAYS

    def _verdict(self, score: int) -> str:
        if score >= 70:
            return "TRUST"
        elif score >= 40:
            return "CAUTION"
        return "REJECT"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trust_engine.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add agent/ tests/test_trust_engine.py
git commit -m "feat: trust engine — weighted scoring, decay, sybil penalty"
```

---

## Task 4: Longevity Analyzer

**Files:**
- Create: `agent/analyzers/longevity.py`
- Test: `tests/test_analyzers.py`

**Step 1: Write the failing test**

```python
# tests/test_analyzers.py
import pytest
from agent.analyzers.longevity import LongevityAnalyzer

def test_longevity_new_wallet():
    analyzer = LongevityAnalyzer()
    # Wallet created today → low score
    score = analyzer.score(wallet_age_days=0, first_tx_days_ago=0)
    assert score <= 20

def test_longevity_old_wallet():
    analyzer = LongevityAnalyzer()
    # Wallet 1 year old → high score
    score = analyzer.score(wallet_age_days=365, first_tx_days_ago=365)
    assert score >= 80

def test_longevity_medium_wallet():
    analyzer = LongevityAnalyzer()
    # Wallet 90 days old
    score = analyzer.score(wallet_age_days=90, first_tx_days_ago=90)
    assert 40 <= score <= 70

def test_longevity_clamped():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=9999, first_tx_days_ago=9999)
    assert score == 100
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyzers.py::test_longevity_new_wallet -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/analyzers/longevity.py

class LongevityAnalyzer:
    """Scores wallet age. Older wallets = more trustworthy."""

    MAX_AGE_DAYS = 365  # 1 year = max score

    def score(self, wallet_age_days: int, first_tx_days_ago: int) -> int:
        age = max(wallet_age_days, first_tx_days_ago)
        raw = min(age / self.MAX_AGE_DAYS, 1.0) * 100
        return min(round(raw), 100)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyzers.py -v -k longevity`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add agent/analyzers/longevity.py tests/test_analyzers.py
git commit -m "feat: longevity analyzer — wallet age scoring"
```

---

## Task 5: Activity Analyzer

**Files:**
- Create: `agent/analyzers/activity.py`
- Modify: `tests/test_analyzers.py`

**Step 1: Write the failing test**

```python
# append to tests/test_analyzers.py
from agent.analyzers.activity import ActivityAnalyzer

def test_activity_no_transactions():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=0, active_days=0, total_days=30)
    assert score <= 10

def test_activity_high():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=500, active_days=200, total_days=365)
    assert score >= 75

def test_activity_moderate():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=50, active_days=30, total_days=90)
    assert 40 <= score <= 75

def test_activity_clamped():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=99999, active_days=365, total_days=365)
    assert score == 100
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyzers.py -v -k activity`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/analyzers/activity.py

class ActivityAnalyzer:
    """Scores transaction frequency and consistency."""

    TX_COUNT_MAX = 500     # 500+ txs = max contribution
    CONSISTENCY_MAX = 0.6  # active 60%+ of days = max contribution

    def score(self, tx_count: int, active_days: int, total_days: int) -> int:
        if total_days == 0:
            return 0

        # Volume component (60% weight)
        volume = min(tx_count / self.TX_COUNT_MAX, 1.0)

        # Consistency component (40% weight) — active_days / total_days
        consistency_ratio = active_days / total_days
        consistency = min(consistency_ratio / self.CONSISTENCY_MAX, 1.0)

        raw = (volume * 0.6 + consistency * 0.4) * 100
        return min(round(raw), 100)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyzers.py -v -k activity`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add agent/analyzers/activity.py tests/test_analyzers.py
git commit -m "feat: activity analyzer — tx frequency and consistency scoring"
```

---

## Task 6: Counterparty Quality Analyzer

**Files:**
- Create: `agent/analyzers/counterparty.py`
- Modify: `tests/test_analyzers.py`

**Step 1: Write the failing test**

```python
# append to tests/test_analyzers.py
from agent.analyzers.counterparty import CounterpartyAnalyzer

def test_counterparty_all_clean():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=50, verified_counterparties=45, flagged_counterparties=0)
    assert score >= 85

def test_counterparty_all_flagged():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=10, verified_counterparties=0, flagged_counterparties=10)
    assert score <= 10

def test_counterparty_mixed():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=20, verified_counterparties=10, flagged_counterparties=3)
    assert 40 <= score <= 75

def test_counterparty_no_interactions():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=0, verified_counterparties=0, flagged_counterparties=0)
    assert score <= 20
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyzers.py -v -k counterparty`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/analyzers/counterparty.py

class CounterpartyAnalyzer:
    """Scores the quality of an agent's interaction partners."""

    DIVERSITY_MAX = 30  # 30+ unique counterparties = max diversity bonus

    def score(self, total_counterparties: int, verified_counterparties: int,
              flagged_counterparties: int) -> int:
        if total_counterparties == 0:
            return 10  # No history = low trust

        # Clean ratio (60% weight) — what fraction is NOT flagged
        flagged_ratio = flagged_counterparties / total_counterparties
        clean_score = (1.0 - flagged_ratio) * 100

        # Verified ratio (25% weight) — what fraction is verified/known-good
        verified_ratio = verified_counterparties / total_counterparties
        verified_score = verified_ratio * 100

        # Diversity bonus (15% weight) — more unique counterparties = better
        diversity = min(total_counterparties / self.DIVERSITY_MAX, 1.0) * 100

        raw = clean_score * 0.60 + verified_score * 0.25 + diversity * 0.15
        return min(round(raw), 100)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyzers.py -v -k counterparty`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add agent/analyzers/counterparty.py tests/test_analyzers.py
git commit -m "feat: counterparty quality analyzer — clean/verified/diversity scoring"
```

---

## Task 7: Contract Risk Analyzer

**Files:**
- Create: `agent/analyzers/contract_risk.py`
- Modify: `tests/test_analyzers.py`

**Step 1: Write the failing test**

```python
# append to tests/test_analyzers.py
from agent.analyzers.contract_risk import ContractRiskAnalyzer

def test_contract_risk_clean():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=30, malicious_contracts=0, unverified_contracts=2)
    assert score >= 85

def test_contract_risk_dangerous():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=10, malicious_contracts=5, unverified_contracts=3)
    assert score <= 25

def test_contract_risk_moderate():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=20, malicious_contracts=1, unverified_contracts=5)
    assert 40 <= score <= 75

def test_contract_risk_no_contracts():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=0, malicious_contracts=0, unverified_contracts=0)
    assert score <= 30
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyzers.py -v -k contract_risk`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/analyzers/contract_risk.py

class ContractRiskAnalyzer:
    """Scores risk from contract interactions."""

    def score(self, total_contracts: int, malicious_contracts: int,
              unverified_contracts: int) -> int:
        if total_contracts == 0:
            return 20  # No contract history = uncertain

        # Malicious ratio is heavily penalized (70% weight)
        malicious_ratio = malicious_contracts / total_contracts
        malicious_score = (1.0 - malicious_ratio) * 100

        # Unverified ratio is moderately penalized (30% weight)
        unverified_ratio = unverified_contracts / total_contracts
        unverified_score = (1.0 - unverified_ratio) * 100

        raw = malicious_score * 0.70 + unverified_score * 0.30
        return min(round(raw), 100)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyzers.py -v -k contract_risk`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add agent/analyzers/contract_risk.py tests/test_analyzers.py
git commit -m "feat: contract risk analyzer — malicious + unverified scoring"
```

---

## Task 8: Sybil Detection

**Files:**
- Create: `agent/sybil.py`
- Test: `tests/test_sybil.py`

**Step 1: Write the failing test**

```python
# tests/test_sybil.py
from agent.sybil import SybilDetector

def test_no_sybil_diverse_interactions():
    detector = SybilDetector()
    edges = {
        1: {"0xa", "0xb", "0xc", "0xd", "0xe"},
        2: {"0xa", "0xf", "0xg", "0xh"},
    }
    clusters = detector.detect(edges)
    assert len(clusters) == 0

def test_sybil_ring_detected():
    detector = SybilDetector()
    # Agents 1, 2, 3 only interact with each other
    edges = {
        1: {"wallet_2", "wallet_3"},
        2: {"wallet_1", "wallet_3"},
        3: {"wallet_1", "wallet_2"},
    }
    wallet_to_agent = {"wallet_1": 1, "wallet_2": 2, "wallet_3": 3}
    clusters = detector.detect(edges, wallet_to_agent)
    assert len(clusters) == 1
    assert set(clusters[0]) == {1, 2, 3}

def test_sybil_needs_minimum_cluster_size():
    detector = SybilDetector()
    # Only 2 agents — below minimum cluster size of 3
    edges = {
        1: {"wallet_2"},
        2: {"wallet_1"},
    }
    wallet_to_agent = {"wallet_1": 1, "wallet_2": 2}
    clusters = detector.detect(edges, wallet_to_agent)
    assert len(clusters) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sybil.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/sybil.py
from typing import Dict, Set, List

MIN_CLUSTER_SIZE = 3
MAX_EXTERNAL_RATIO = 0.2  # If >80% of interactions are within cluster → sybil

class SybilDetector:
    def detect(self, edges: Dict[int, Set[str]],
               wallet_to_agent: Dict[str, int] = None) -> List[List[int]]:
        if wallet_to_agent is None:
            wallet_to_agent = {}

        agent_ids = list(edges.keys())
        if len(agent_ids) < MIN_CLUSTER_SIZE:
            return []

        # Build agent-to-agent interaction graph
        agent_graph: Dict[int, Set[int]] = {a: set() for a in agent_ids}
        for agent_id, counterparties in edges.items():
            for cp in counterparties:
                if cp in wallet_to_agent:
                    other = wallet_to_agent[cp]
                    if other != agent_id:
                        agent_graph[agent_id].add(other)

        # Find cliques — groups where each member interacts with all others
        clusters = []
        visited = set()
        for agent_id in agent_ids:
            if agent_id in visited:
                continue
            cluster = self._expand_cluster(agent_id, agent_graph, edges, wallet_to_agent)
            if len(cluster) >= MIN_CLUSTER_SIZE:
                clusters.append(sorted(cluster))
                visited.update(cluster)

        return clusters

    def _expand_cluster(self, start: int, agent_graph: Dict[int, Set[int]],
                        edges: Dict[int, Set[str]],
                        wallet_to_agent: Dict[str, int]) -> List[int]:
        cluster = {start}
        candidates = agent_graph.get(start, set())
        for candidate in candidates:
            # Check if candidate interacts with all current cluster members
            candidate_peers = agent_graph.get(candidate, set())
            if cluster.issubset(candidate_peers | {candidate}):
                cluster.add(candidate)

        # Verify cluster is isolated — most interactions are internal
        for member in list(cluster):
            total = len(edges.get(member, set()))
            internal = len(agent_graph.get(member, set()) & cluster)
            if total > 0 and internal / total < (1 - MAX_EXTERNAL_RATIO):
                cluster.discard(member)

        return list(cluster)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sybil.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add agent/sybil.py tests/test_sybil.py
git commit -m "feat: sybil detection — cluster analysis on interaction graph"
```

---

## Task 9: On-Chain Data Fetcher (Base + Ethereum)

**Files:**
- Create: `agent/chain.py`
- Test: `tests/test_chain.py`

This module wraps web3.py to fetch wallet data from Base and Ethereum RPCs. It provides the raw data that the 4 analyzers consume.

**Step 1: Write the failing test**

```python
# tests/test_chain.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.chain import ChainFetcher, WalletData

@pytest.mark.asyncio
async def test_fetch_wallet_data_combines_chains():
    fetcher = ChainFetcher.__new__(ChainFetcher)
    fetcher._fetch_chain = AsyncMock(side_effect=[
        {"tx_count": 50, "first_tx_timestamp": 1700000000, "contracts": ["0xa"], "counterparties": {"0xb"}},
        {"tx_count": 100, "first_tx_timestamp": 1690000000, "contracts": ["0xc"], "counterparties": {"0xd"}},
    ])
    data = await fetcher.fetch_wallet("0xabc")
    assert data.tx_count == 150
    assert len(data.counterparties) == 2

def test_wallet_data_age_days():
    import time
    data = WalletData(
        tx_count=10,
        first_tx_timestamp=int(time.time()) - 86400 * 30,
        contracts=[], counterparties=set(),
        malicious_contracts=0, verified_counterparties=0,
        flagged_counterparties=0, unverified_contracts=0,
        active_days=10, total_days=30,
    )
    assert 29 <= data.wallet_age_days <= 31
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_chain.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# agent/chain.py
import time
from dataclasses import dataclass, field
from typing import Set, List

@dataclass
class WalletData:
    tx_count: int
    first_tx_timestamp: int
    contracts: List[str]
    counterparties: Set[str]
    malicious_contracts: int
    verified_counterparties: int
    flagged_counterparties: int
    unverified_contracts: int
    active_days: int
    total_days: int

    @property
    def wallet_age_days(self) -> int:
        if self.first_tx_timestamp == 0:
            return 0
        return max(0, int((time.time() - self.first_tx_timestamp) / 86400))

class ChainFetcher:
    def __init__(self, base_rpc: str, eth_rpc: str):
        self.base_rpc = base_rpc
        self.eth_rpc = eth_rpc

    async def fetch_wallet(self, address: str) -> WalletData:
        base_data = await self._fetch_chain(address, self.base_rpc, "base")
        eth_data = await self._fetch_chain(address, self.eth_rpc, "ethereum")

        all_counterparties = base_data["counterparties"] | eth_data["counterparties"]
        all_contracts = base_data["contracts"] + eth_data["contracts"]
        first_tx = min(
            base_data["first_tx_timestamp"] or float("inf"),
            eth_data["first_tx_timestamp"] or float("inf"),
        )
        if first_tx == float("inf"):
            first_tx = 0

        return WalletData(
            tx_count=base_data["tx_count"] + eth_data["tx_count"],
            first_tx_timestamp=int(first_tx),
            contracts=all_contracts,
            counterparties=all_counterparties,
            malicious_contracts=0,  # enriched later
            verified_counterparties=0,  # enriched later
            flagged_counterparties=0,  # enriched later
            unverified_contracts=0,  # enriched later
            active_days=base_data.get("active_days", 0) + eth_data.get("active_days", 0),
            total_days=max(base_data.get("total_days", 0), eth_data.get("total_days", 0)),
        )

    async def _fetch_chain(self, address: str, rpc_url: str, chain: str) -> dict:
        """Fetch wallet data from a single chain via RPC + block explorer APIs."""
        # Implementation uses Etherscan/BaseScan API for tx history
        # Placeholder — real implementation calls etherscan API
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        tx_count = w3.eth.get_transaction_count(Web3.to_checksum_address(address))

        return {
            "tx_count": tx_count,
            "first_tx_timestamp": 0,
            "contracts": [],
            "counterparties": set(),
            "active_days": 0,
            "total_days": 0,
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_chain.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add agent/chain.py tests/test_chain.py
git commit -m "feat: chain fetcher — Base + Ethereum wallet data aggregation"
```

---

## Task 10: ERC-8004 Registry Client

**Files:**
- Create: `agent/erc8004.py`
- Create: `agent/abis/` (ABI JSON files)
- Test: `tests/test_erc8004.py`

**Step 1: Fetch ABIs from BaseScan for the Identity Registry contract**

Go to `https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432#code` and save the ABI. Create `agent/abis/identity_registry.json`, `agent/abis/reputation_registry.json`, `agent/abis/validation_registry.json`.

If ABIs are not verified, use the function signatures from the ERC-8004 spec to build minimal ABIs.

**Step 2: Write the failing test**

```python
# tests/test_erc8004.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.erc8004 import ERC8004Client

def test_parse_agent_uri():
    client = ERC8004Client.__new__(ERC8004Client)
    registration = client._parse_registration_json('{"name":"TestAgent","services":[],"active":true}')
    assert registration["name"] == "TestAgent"
    assert registration["active"] is True

def test_build_feedback_params():
    client = ERC8004Client.__new__(ERC8004Client)
    params = client._build_feedback_params(
        agent_id=42, value=73, tag1="trustScore",
        tag2="sentinelnet-v1", feedback_uri="ipfs://abc", feedback_hash=b"\x00" * 32
    )
    assert params["agent_id"] == 42
    assert params["value"] == 73
    assert params["tag1"] == "trustScore"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_erc8004.py -v`
Expected: FAIL

**Step 4: Write minimal implementation**

```python
# agent/erc8004.py
import json
from typing import Optional, List
from web3 import Web3

class ERC8004Client:
    def __init__(self, w3: Web3, identity_addr: str,
                 reputation_addr: str, validation_addr: str,
                 private_key: str, agent_id: int):
        self.w3 = w3
        self.identity_addr = Web3.to_checksum_address(identity_addr)
        self.reputation_addr = Web3.to_checksum_address(reputation_addr) if reputation_addr else None
        self.validation_addr = Web3.to_checksum_address(validation_addr) if validation_addr else None
        self.private_key = private_key
        self.agent_id = agent_id
        self.account = w3.eth.account.from_key(private_key) if private_key else None

    async def get_total_agents(self) -> int:
        """Get total registered agents from Identity Registry."""
        # Uses totalSupply() from ERC-721
        # Placeholder — real implementation calls contract
        return 0

    async def get_agent_wallet(self, agent_id: int) -> Optional[str]:
        """Get wallet address for an agent from Identity Registry."""
        # Uses getAgentWallet(agentId)
        return None

    async def get_agent_uri(self, agent_id: int) -> Optional[str]:
        """Get registration URI for an agent."""
        # Uses tokenURI(agentId)
        return None

    async def give_feedback(self, agent_id: int, value: int, tag1: str,
                           tag2: str, feedback_uri: str, feedback_hash: bytes) -> str:
        """Post feedback to Reputation Registry. Returns tx hash."""
        params = self._build_feedback_params(agent_id, value, tag1, tag2,
                                              feedback_uri, feedback_hash)
        # Build and send transaction
        return ""

    async def validation_response(self, request_hash: bytes, response: int,
                                  response_uri: str, response_hash: bytes,
                                  tag: str) -> str:
        """Post validation response. Returns tx hash."""
        return ""

    def _parse_registration_json(self, raw: str) -> dict:
        return json.loads(raw)

    def _build_feedback_params(self, agent_id: int, value: int, tag1: str,
                                tag2: str, feedback_uri: str,
                                feedback_hash: bytes) -> dict:
        return {
            "agent_id": agent_id,
            "value": value,
            "value_decimals": 0,
            "tag1": tag1,
            "tag2": tag2,
            "feedback_uri": feedback_uri,
            "feedback_hash": feedback_hash,
        }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_erc8004.py -v`
Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add agent/erc8004.py agent/abis/ tests/test_erc8004.py
git commit -m "feat: ERC-8004 registry client — identity, reputation, validation"
```

---

## Task 11: IPFS Publisher

**Files:**
- Create: `agent/publisher.py`
- Test: `tests/test_publisher.py`

**Step 1: Write the failing test**

```python
# tests/test_publisher.py
import pytest
from unittest.mock import AsyncMock, patch
from agent.publisher import Publisher

def test_build_evidence_json():
    pub = Publisher.__new__(Publisher)
    evidence = pub._build_evidence(
        agent_id=42, wallet="0xabc",
        trust_score=73, longevity=85, activity=68,
        counterparty=79, contract_risk=62, verdict="TRUST",
        chains=["base", "ethereum"],
    )
    assert evidence["agent_id"] == 42
    assert evidence["trust_score"] == 73
    assert "scored_at" in evidence
    assert evidence["scorer"] == "sentinelnet-v1"

@pytest.mark.asyncio
async def test_pin_to_ipfs_returns_cid():
    pub = Publisher.__new__(Publisher)
    pub._http_post = AsyncMock(return_value={"IpfsHash": "QmTest123"})
    pub.pinata_api_key = "key"
    pub.pinata_secret_key = "secret"
    cid = await pub.pin_json({"test": True})
    assert cid == "ipfs://QmTest123"
```

**Step 2: Run test, verify fails, write implementation**

```python
# agent/publisher.py
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional
import httpx

class Publisher:
    PINATA_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

    def __init__(self, pinata_api_key: str, pinata_secret_key: str,
                 erc8004_client=None):
        self.pinata_api_key = pinata_api_key
        self.pinata_secret_key = pinata_secret_key
        self.erc8004 = erc8004_client

    async def publish(self, agent_id: int, wallet: str, trust_score: int,
                      longevity: int, activity: int, counterparty: int,
                      contract_risk: int, verdict: str) -> dict:
        evidence = self._build_evidence(
            agent_id, wallet, trust_score, longevity, activity,
            counterparty, contract_risk, verdict, ["base", "ethereum"]
        )
        evidence_uri = await self.pin_json(evidence)
        evidence_hash = hashlib.sha256(json.dumps(evidence).encode()).digest()

        # Post 5 scores to Reputation Registry
        tags = [
            ("trustScore", trust_score),
            ("longevity", longevity),
            ("activity", activity),
            ("counterparty", counterparty),
            ("contractRisk", contract_risk),
        ]
        tx_hashes = []
        if self.erc8004:
            for tag, value in tags:
                tx = await self.erc8004.give_feedback(
                    agent_id, value, tag, "sentinelnet-v1",
                    evidence_uri, evidence_hash,
                )
                tx_hashes.append(tx)

        return {
            "evidence_uri": evidence_uri,
            "feedback_txs": tx_hashes,
        }

    async def pin_json(self, data: dict) -> str:
        resp = await self._http_post(
            self.PINATA_URL,
            json={"pinataContent": data},
            headers={
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_key": self.pinata_secret_key,
            },
        )
        return f"ipfs://{resp['IpfsHash']}"

    async def _http_post(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, **kwargs)
            r.raise_for_status()
            return r.json()

    def _build_evidence(self, agent_id, wallet, trust_score, longevity,
                        activity, counterparty, contract_risk, verdict, chains):
        return {
            "agent_id": agent_id,
            "wallet": wallet,
            "trust_score": trust_score,
            "breakdown": {
                "longevity": longevity,
                "activity": activity,
                "counterparty_quality": counterparty,
                "contract_risk": contract_risk,
            },
            "verdict": verdict,
            "chains_analyzed": chains,
            "scorer": "sentinelnet-v1",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
```

**Step 3: Run test, commit**

Run: `pytest tests/test_publisher.py -v`
Expected: PASS (2 tests)

```bash
git add agent/publisher.py tests/test_publisher.py
git commit -m "feat: publisher — IPFS pinning + Reputation Registry posting"
```

---

## Task 12: Discovery Sweep + Event Listener

**Files:**
- Create: `agent/discovery.py`
- Test: `tests/test_discovery.py`

**Step 1: Write the failing test**

```python
# tests/test_discovery.py
import pytest
from unittest.mock import AsyncMock
from agent.discovery import Discovery

@pytest.mark.asyncio
async def test_find_new_agents():
    discovery = Discovery.__new__(Discovery)
    discovery.erc8004 = AsyncMock()
    discovery.erc8004.get_total_agents = AsyncMock(return_value=100)
    discovery.db = AsyncMock()
    discovery.db.get_all_scores = AsyncMock(return_value=[
        {"agent_id": i} for i in range(95)
    ])
    discovery.self_agent_id = 999

    new_ids = await discovery.find_new_agents()
    # 100 total - 95 scored - self (999 not in range) = 5 new
    assert len(new_ids) == 5

@pytest.mark.asyncio
async def test_find_stale_agents():
    discovery = Discovery.__new__(Discovery)
    discovery.db = AsyncMock()
    discovery.db.get_all_scores = AsyncMock(return_value=[
        {"agent_id": 1, "scored_at": "2026-01-01T00:00:00+00:00"},
        {"agent_id": 2, "scored_at": "2026-03-15T00:00:00+00:00"},
    ])
    discovery.rescore_after_hours = 24

    stale = await discovery.find_stale_agents()
    assert 1 in stale
    assert 2 not in stale
```

**Step 2: Write implementation, run tests, commit**

```python
# agent/discovery.py
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class Discovery:
    def __init__(self, erc8004, db, pipeline, self_agent_id: int,
                 sweep_interval: int = 1800, rescore_after_hours: int = 24):
        self.erc8004 = erc8004
        self.db = db
        self.pipeline = pipeline
        self.self_agent_id = self_agent_id
        self.sweep_interval = sweep_interval
        self.rescore_after_hours = rescore_after_hours
        self._running = False

    async def find_new_agents(self) -> list:
        total = await self.erc8004.get_total_agents()
        scored = await self.db.get_all_scores()
        scored_ids = {s["agent_id"] for s in scored}
        new_ids = [
            i for i in range(1, total + 1)
            if i not in scored_ids and i != self.self_agent_id
        ]
        return new_ids

    async def find_stale_agents(self) -> list:
        scores = await self.db.get_all_scores()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.rescore_after_hours)
        stale = []
        for s in scores:
            scored_at = datetime.fromisoformat(s["scored_at"])
            if scored_at < cutoff:
                stale.append(s["agent_id"])
        return stale

    async def sweep(self):
        logger.info("Discovery sweep started")
        new_agents = await self.find_new_agents()
        stale_agents = await self.find_stale_agents()
        targets = list(set(new_agents + stale_agents))
        logger.info(f"Sweep: {len(new_agents)} new, {len(stale_agents)} stale, {len(targets)} total targets")
        for agent_id in targets:
            try:
                await self.pipeline(agent_id)
            except Exception as e:
                logger.error(f"Failed to score agent {agent_id}: {e}")
        logger.info("Discovery sweep complete")

    async def run_loop(self):
        self._running = True
        while self._running:
            await self.sweep()
            await asyncio.sleep(self.sweep_interval)

    def stop(self):
        self._running = False
```

Run: `pytest tests/test_discovery.py -v`
Expected: PASS (2 tests)

```bash
git add agent/discovery.py tests/test_discovery.py
git commit -m "feat: discovery — sweep loop + stale agent detection"
```

---

## Task 13: Validator Responder

**Files:**
- Create: `agent/validator.py`
- Test: `tests/test_validator.py`

**Step 1: Write test, implement, commit**

Validator listens for `ValidationRequest` events and runs the pipeline + posts response. Test with mocked ERC-8004 client.

```bash
git add agent/validator.py tests/test_validator.py
git commit -m "feat: validator responder — on-demand trust assessment"
```

---

## Task 14: Alerts Module

**Files:**
- Create: `agent/alerts.py`
- Test: `tests/test_alerts.py`

**Step 1: Write the failing test**

```python
# tests/test_alerts.py
from agent.alerts import AlertChecker

def test_alert_triggered_on_large_drop():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=55) is True

def test_no_alert_on_small_change():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=75) is False

def test_no_alert_on_improvement():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=60, new_score=80) is False

def test_alert_on_exact_threshold():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=60) is True
```

**Step 2: Write implementation**

```python
# agent/alerts.py
import logging

logger = logging.getLogger(__name__)

class AlertChecker:
    def __init__(self, threshold: int = 20):
        self.threshold = threshold

    def should_alert(self, previous_score: int, new_score: int) -> bool:
        drop = previous_score - new_score
        return drop >= self.threshold
```

Run: `pytest tests/test_alerts.py -v`
Expected: PASS (4 tests)

```bash
git add agent/alerts.py tests/test_alerts.py
git commit -m "feat: alert checker — trust degradation detection"
```

---

## Task 15: Trust Graph

**Files:**
- Create: `agent/graph.py`
- Test: `tests/test_graph.py`

Simple module that reads graph edges from DB and returns an agent's trust neighborhood.

```bash
git add agent/graph.py tests/test_graph.py
git commit -m "feat: trust graph — agent neighborhood queries"
```

---

## Task 16: SentinelNetStaking Smart Contract

**Files:**
- Create: `contracts/SentinelNetStaking.sol`
- Create: `contracts/hardhat.config.js`
- Create: `contracts/package.json`

**Step 1: Write the contract**

```solidity
// contracts/SentinelNetStaking.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SentinelNetStaking {
    struct Stake {
        uint256 agentId;
        uint8 score;
        uint256 amount;
        uint256 stakedAt;
        bool challenged;
        bool resolved;
    }

    address public sentinel;
    uint256 public challengeWindow = 72 hours;
    mapping(bytes32 => Stake) public stakes;

    event ScoreStaked(uint256 indexed agentId, uint8 score, uint256 amount, bytes32 stakeId);
    event StakeChallenged(bytes32 indexed stakeId, address challenger);
    event TrustDegraded(uint256 indexed agentId, uint8 previousScore, uint8 newScore, uint256 timestamp);

    constructor() {
        sentinel = msg.sender;
    }

    function stakeScore(uint256 agentId, uint8 score) external payable {
        require(msg.sender == sentinel, "Only sentinel");
        require(msg.value > 0, "Must stake ETH");
        bytes32 stakeId = keccak256(abi.encodePacked(agentId, score, block.timestamp));
        stakes[stakeId] = Stake(agentId, score, msg.value, block.timestamp, false, false);
        emit ScoreStaked(agentId, score, msg.value, stakeId);
    }

    function challenge(bytes32 stakeId) external {
        Stake storage s = stakes[stakeId];
        require(s.amount > 0, "No stake");
        require(!s.challenged, "Already challenged");
        require(block.timestamp <= s.stakedAt + challengeWindow, "Window closed");
        s.challenged = true;
        emit StakeChallenged(stakeId, msg.sender);
    }

    function resolveChallenge(bytes32 stakeId, bool challengeSucceeded) external {
        require(msg.sender == sentinel, "Only sentinel");
        Stake storage s = stakes[stakeId];
        require(s.challenged, "Not challenged");
        require(!s.resolved, "Already resolved");
        s.resolved = true;
        // If challenge succeeded, stake is lost (stays in contract for now)
        // If failed, sentinel can withdraw
    }

    function withdraw(bytes32 stakeId) external {
        require(msg.sender == sentinel, "Only sentinel");
        Stake storage s = stakes[stakeId];
        require(s.amount > 0, "No stake");
        require(block.timestamp > s.stakedAt + challengeWindow, "Window open");
        require(!s.challenged || s.resolved, "Pending challenge");
        uint256 amount = s.amount;
        s.amount = 0;
        payable(sentinel).transfer(amount);
    }

    function emitTrustDegraded(uint256 agentId, uint8 prev, uint8 next) external {
        require(msg.sender == sentinel, "Only sentinel");
        emit TrustDegraded(agentId, prev, next, block.timestamp);
    }
}
```

**Step 2: Hardhat config + deploy script**

```bash
cd contracts && npm init -y && npm install hardhat @nomicfoundation/hardhat-toolbox
npx hardhat compile
```

**Step 3: Deploy to Base mainnet**

```bash
npx hardhat run scripts/deploy.js --network base
```

**Step 4: Commit**

```bash
git add contracts/
git commit -m "feat: SentinelNetStaking contract — score staking + challenge"
```

---

## Task 17: FastAPI REST Server

**Files:**
- Create: `api.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

```python
# tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from api import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "sentinelnet"

@pytest.mark.asyncio
async def test_trust_endpoint_404_for_unknown():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/99999")
    assert r.status_code == 404
```

**Step 2: Write implementation**

```python
# api.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from db import Database

app = FastAPI(title="SentinelNet", version="1.0.0")
db = Database()

@app.on_event("startup")
async def startup():
    await db.init()

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sentinelnet"}

@app.get("/trust/{agent_id}")
async def get_trust(agent_id: int):
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    return score

@app.get("/trust/graph/{agent_id}")
async def get_trust_graph(agent_id: int):
    edges = await db.get_edges(agent_id)
    return {"agent_id": agent_id, "neighbors": edges}

@app.get("/dashboard")
async def dashboard():
    return FileResponse("dashboard/index.html")

@app.get("/api/stats")
async def stats():
    scores = await db.get_all_scores()
    return {
        "agents_scored": len(scores),
        "avg_trust_score": sum(s["trust_score"] for s in scores) / len(scores) if scores else 0,
    }
```

Run: `pytest tests/test_api.py -v`
Expected: PASS

```bash
git add api.py tests/test_api.py
git commit -m "feat: FastAPI REST server — health, trust, graph, stats endpoints"
```

---

## Task 18: MCP Server

**Files:**
- Create: `mcp/server.py`
- Test: `tests/test_mcp.py`

Exposes `check_trust` tool via MCP Python SDK. Wraps the same logic as the REST endpoint.

```bash
git add mcp/ tests/test_mcp.py
git commit -m "feat: MCP server — check_trust tool for agent-to-agent use"
```

---

## Task 19: Live Dashboard

**Files:**
- Create: `dashboard/index.html`

Single HTML file with embedded CSS/JS. Fetches `/api/stats` and `/trust/` endpoints. Auto-refreshes every 15 seconds. Shows: agents discovered, latest scores, sweep status, sybil clusters, trust degradation alerts.

```bash
git add dashboard/
git commit -m "feat: live dashboard — real-time trust monitoring UI"
```

---

## Task 20: Agent Orchestrator (Wire Everything Together)

**Files:**
- Modify: `agent/__init__.py`

Wires all components: config → chain fetcher → analyzers → trust engine → sybil detector → publisher → staker → alerts → discovery → validator. Starts the autonomous loop.

```python
# agent/__init__.py
import asyncio
import logging
from config import Settings
from db import Database
from agent.chain import ChainFetcher
from agent.trust_engine import TrustEngine
from agent.sybil import SybilDetector
from agent.publisher import Publisher
from agent.discovery import Discovery
from agent.alerts import AlertChecker
from agent.erc8004 import ERC8004Client
from agent.analyzers.longevity import LongevityAnalyzer
from agent.analyzers.activity import ActivityAnalyzer
from agent.analyzers.counterparty import CounterpartyAnalyzer
from agent.analyzers.contract_risk import ContractRiskAnalyzer

logger = logging.getLogger(__name__)

class SentinelNetAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database()
        self.chain = ChainFetcher(settings.BASE_RPC_URL, settings.ETH_RPC_URL)
        self.engine = TrustEngine()
        self.sybil = SybilDetector()
        self.alerts = AlertChecker()

        # Analyzers
        self.longevity = LongevityAnalyzer()
        self.activity = ActivityAnalyzer()
        self.counterparty = CounterpartyAnalyzer()
        self.contract_risk = ContractRiskAnalyzer()

    async def start(self):
        await self.db.init()
        logger.info("SentinelNet agent started")
        self.discovery = Discovery(
            erc8004=self.erc8004,
            db=self.db,
            pipeline=self.analyze_agent,
            self_agent_id=self.settings.SENTINELNET_AGENT_ID,
            sweep_interval=self.settings.SWEEP_INTERVAL_SECONDS,
        )
        asyncio.create_task(self.discovery.run_loop())

    async def analyze_agent(self, agent_id: int) -> dict:
        wallet = await self.erc8004.get_agent_wallet(agent_id)
        if not wallet:
            return None

        data = await self.chain.fetch_wallet(wallet)

        longevity = self.longevity.score(data.wallet_age_days, data.wallet_age_days)
        activity = self.activity.score(data.tx_count, data.active_days, data.total_days)
        counterparty = self.counterparty.score(
            len(data.counterparties), data.verified_counterparties, data.flagged_counterparties
        )
        contract_risk = self.contract_risk.score(
            len(data.contracts), data.malicious_contracts, data.unverified_contracts
        )

        result = self.engine.compute(longevity, activity, counterparty, contract_risk)

        # Check for trust degradation
        existing = await self.db.get_score(agent_id)
        if existing:
            if self.alerts.should_alert(existing["trust_score"], result.trust_score):
                logger.warning(f"TrustDegraded: agent {agent_id} dropped {existing['trust_score']} → {result.trust_score}")

        # Publish to chain + IPFS
        pub_result = await self.publisher.publish(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk, result.verdict
        )

        # Save to local cache
        await self.db.save_score(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk,
            result.verdict, pub_result.get("feedback_txs", [""])[0],
            pub_result.get("evidence_uri", ""),
        )

        return result
```

```bash
git add agent/__init__.py
git commit -m "feat: agent orchestrator — wire all components together"
```

---

## Task 21: README

**Files:**
- Create: `README.md`

Cover: what SentinelNet is, architecture diagram, how to run, MCP tool usage, API reference, ERC-8004 integration, 12 features list, hackathon submission info.

```bash
git add README.md
git commit -m "docs: README — project overview, setup, API reference"
```

---

## Task 22: GitHub Repo + Push

```bash
gh repo create Ridwannurudeen/sentinelnet --public --description "Autonomous agent reputation watchdog for ERC-8004 on Base" --source . --push
```

---

## Task 23: Hackathon Submission

Use the Synthesis API to create and submit the project:

```bash
curl -X POST https://synthesis.devfolio.co/projects \
  -H "Authorization: Bearer sk-synth-..." \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Include conversation log from the brainstorming session.

---

## Day-by-Day Schedule

| Day | Date | Tasks | Target |
|-----|------|-------|--------|
| 1 | Mar 15 | Tasks 1-4 | Foundation + config + db + trust engine + longevity |
| 2 | Mar 16 | Tasks 5-8 | Activity + counterparty + contract risk + sybil |
| 3 | Mar 17 | Tasks 9-11 | Chain fetcher + ERC-8004 client + publisher |
| 4 | Mar 18 | Tasks 12-15 | Discovery + validator + alerts + graph |
| 5 | Mar 19 | Task 16 | Smart contract — deploy to Base |
| 6 | Mar 20 | Tasks 17-19 | REST API + MCP server + dashboard |
| 7 | Mar 21 | Tasks 20-21 | Orchestrator + README |
| 8 | Mar 22 | Tasks 22-23 | Push to GitHub + submit to hackathon |
