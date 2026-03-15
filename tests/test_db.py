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
