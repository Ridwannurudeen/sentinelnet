# tests/test_contagion.py
from agent.contagion import ContagionEngine


def test_no_adjustment_when_no_edges():
    engine = ContagionEngine()
    scores = {1: {"trust_score": 60, "wallet": "0xa", "verdict": "TRUST"}}
    result = engine.compute_adjustments(scores, [])
    assert result == {}


def test_negative_contagion_from_reject_neighbor():
    engine = ContagionEngine()
    scores = {
        1: {"trust_score": 60, "wallet": "0xa", "verdict": "TRUST"},
        2: {"trust_score": 20, "wallet": "0xb", "verdict": "REJECT"},
    }
    edges = [
        {"agent_id": 1, "counterparty": "0xb", "interaction_count": 5},
    ]
    result = engine.compute_adjustments(scores, edges)
    # Agent 1 should get negative adjustment from interacting with REJECT agent 2
    assert 1 in result
    assert result[1] < 0


def test_positive_contagion_from_trusted_neighbor():
    engine = ContagionEngine()
    scores = {
        1: {"trust_score": 45, "wallet": "0xa", "verdict": "CAUTION"},
        2: {"trust_score": 90, "wallet": "0xb", "verdict": "TRUST"},
    }
    edges = [
        {"agent_id": 1, "counterparty": "0xb", "interaction_count": 10},
    ]
    result = engine.compute_adjustments(scores, edges)
    # Agent 1 may get positive adjustment from interacting with high-trust agent 2
    if 1 in result:
        assert result[1] > 0


def test_adjustment_capped():
    engine = ContagionEngine()
    scores = {
        1: {"trust_score": 60, "wallet": "0xa", "verdict": "TRUST"},
        2: {"trust_score": 5, "wallet": "0xb", "verdict": "REJECT"},
    }
    edges = [
        {"agent_id": 1, "counterparty": "0xb", "interaction_count": 100},
    ]
    result = engine.compute_adjustments(scores, edges)
    if 1 in result:
        assert result[1] >= -15  # Max negative cap
        assert result[1] <= 10   # Max positive cap
