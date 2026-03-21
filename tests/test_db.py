# tests/test_db.py
import pytest
import asyncio
from db import Database

@pytest.fixture
def db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    d = Database(":memory:")
    loop.run_until_complete(d.init())
    yield d
    loop.run_until_complete(d.close())
    loop.close()

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
            agent_identity=80,
        )
    )
    score = asyncio.get_event_loop().run_until_complete(db.get_score(42))
    assert score["trust_score"] == 73
    assert score["verdict"] == "TRUST"
    assert score["longevity"] == 85
    assert score["agent_identity"] == 80

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
        db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "0x1", "ipfs://1", agent_identity=75)
    )
    asyncio.get_event_loop().run_until_complete(
        db.save_score(2, "0xb", 30, 30, 30, 30, 30, "REJECT", "0x2", "ipfs://2", agent_identity=20)
    )
    all_scores = asyncio.get_event_loop().run_until_complete(db.get_all_scores())
    assert len(all_scores) == 2

def test_score_history_recorded(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_score(42, "0xabc", 73, 85, 68, 79, 62, "TRUST", "0xtx1", "ipfs://abc", agent_identity=80)
    )
    asyncio.get_event_loop().run_until_complete(
        db.save_score(42, "0xabc", 65, 80, 60, 75, 55, "TRUST", "0xtx2", "ipfs://def", agent_identity=70)
    )
    history = asyncio.get_event_loop().run_until_complete(db.get_score_history(42))
    assert len(history) == 2
    # Most recent first
    assert history[0]["trust_score"] == 65
    assert history[1]["trust_score"] == 73

def test_sybil_flagged_persisted(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_score(42, "0xabc", 50, 70, 60, 70, 60, "CAUTION", "", "", agent_identity=50, sybil_flagged=True)
    )
    score = asyncio.get_event_loop().run_until_complete(db.get_score(42))
    assert score["sybil_flagged"] == 1

def test_edge_interaction_count_accumulates(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_edge(agent_id=42, counterparty="0xdef", interaction_count=1, is_flagged=False)
    )
    asyncio.get_event_loop().run_until_complete(
        db.save_edge(agent_id=42, counterparty="0xdef", interaction_count=1, is_flagged=False)
    )
    edges = asyncio.get_event_loop().run_until_complete(db.get_edges(42))
    assert len(edges) == 1
    assert edges[0]["interaction_count"] == 2

def test_get_all_edges(db):
    asyncio.get_event_loop().run_until_complete(
        db.save_edge(42, "0xaaa", 1, False)
    )
    asyncio.get_event_loop().run_until_complete(
        db.save_edge(43, "0xbbb", 1, False)
    )
    all_edges = asyncio.get_event_loop().run_until_complete(db.get_all_edges())
    assert len(all_edges) == 2
