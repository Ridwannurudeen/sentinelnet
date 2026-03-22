# tests/test_anomalies.py
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from api import app, db, _detect_anomalies, _anomaly_cache


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    db.path = ":memory:"
    await db.init()
    # Invalidate anomaly cache between tests
    _anomaly_cache["anomalies"] = None
    _anomaly_cache["checked"] = 0
    _anomaly_cache["ts"] = 0
    yield
    await db.close()


def _transport():
    return ASGITransport(app=app)


# ─── Rapid Score Drop ───

@pytest.mark.asyncio
async def test_rapid_drop_detected():
    """Agent whose score dropped >15 points triggers rapid_drop anomaly."""
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    await db.save_score(1, "0xa", 55, 55, 55, 55, 55, "CAUTION", "", "", agent_identity=50)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    data = r.json()
    assert r.status_code == 200
    drops = [a for a in data["anomalies"] if a["type"] == "rapid_drop"]
    assert len(drops) == 1
    assert drops[0]["severity"] == "HIGH"
    assert drops[0]["agent_id"] == 1
    assert drops[0]["previous_score"] == 80
    assert drops[0]["current_score"] == 55


@pytest.mark.asyncio
async def test_rapid_drop_medium_severity():
    """Drop between 15-24 points is MEDIUM severity."""
    await db.save_score(1, "0xa", 60, 60, 60, 60, 60, "TRUST", "", "", agent_identity=50)
    await db.save_score(1, "0xa", 44, 44, 44, 44, 44, "CAUTION", "", "", agent_identity=40)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    drops = [a for a in r.json()["anomalies"] if a["type"] == "rapid_drop"]
    assert len(drops) == 1
    assert drops[0]["severity"] == "MEDIUM"


@pytest.mark.asyncio
async def test_no_rapid_drop_for_small_change():
    """Score change <15 should not trigger rapid_drop."""
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    await db.save_score(1, "0xa", 70, 70, 70, 70, 70, "TRUST", "", "", agent_identity=65)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    drops = [a for a in r.json()["anomalies"] if a["type"] == "rapid_drop"]
    assert len(drops) == 0


# ─── Suspicious Perfect Scores ───

@pytest.mark.asyncio
async def test_suspicious_perfect_score_low_activity():
    """Score=100 with low activity triggers suspicious_perfect_score."""
    await db.save_score(1, "0xa", 100, 80, 20, 80, 80, "TRUST", "", "", agent_identity=90)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    perfects = [a for a in r.json()["anomalies"] if a["type"] == "suspicious_perfect_score"]
    assert len(perfects) == 1
    assert perfects[0]["severity"] == "HIGH"


@pytest.mark.asyncio
async def test_suspicious_perfect_score_low_longevity():
    """Score=100 with low longevity triggers suspicious_perfect_score."""
    await db.save_score(1, "0xa", 100, 10, 80, 80, 80, "TRUST", "", "", agent_identity=90)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    perfects = [a for a in r.json()["anomalies"] if a["type"] == "suspicious_perfect_score"]
    assert len(perfects) == 1


@pytest.mark.asyncio
async def test_no_perfect_score_anomaly_when_legitimate():
    """Score=100 with high activity AND high longevity should not trigger."""
    await db.save_score(1, "0xa", 100, 80, 80, 80, 80, "TRUST", "", "", agent_identity=90)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    perfects = [a for a in r.json()["anomalies"] if a["type"] == "suspicious_perfect_score"]
    assert len(perfects) == 0


# ─── Sybil Clusters ───

@pytest.mark.asyncio
async def test_sybil_cluster_detected():
    """3+ agents sharing one wallet triggers sybil_cluster."""
    await db.save_score(1, "0xSAME", 60, 60, 60, 60, 60, "TRUST", "", "")
    await db.save_score(2, "0xSAME", 55, 55, 55, 55, 55, "CAUTION", "", "")
    await db.save_score(3, "0xSAME", 50, 50, 50, 50, 50, "CAUTION", "", "")
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    sybils = [a for a in r.json()["anomalies"] if a["type"] == "sybil_cluster"]
    assert len(sybils) == 1
    assert sybils[0]["severity"] == "HIGH"
    assert sorted(sybils[0]["affected_agents"]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_no_sybil_cluster_for_two_agents():
    """Only 2 agents sharing a wallet should NOT trigger sybil_cluster (needs 3+)."""
    await db.save_score(1, "0xSAME", 60, 60, 60, 60, 60, "TRUST", "", "")
    await db.save_score(2, "0xSAME", 55, 55, 55, 55, 55, "CAUTION", "", "")
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    sybils = [a for a in r.json()["anomalies"] if a["type"] == "sybil_cluster"]
    assert len(sybils) == 0


# ─── Score Outliers ───

@pytest.mark.asyncio
async def test_score_outlier_detected():
    """Agent with score >2 std devs from mean triggers score_outlier."""
    # Create 5+ agents with similar scores, then one extreme outlier
    for i in range(1, 6):
        await db.save_score(i, f"0x{i:040x}", 50, 50, 50, 50, 50, "CAUTION", "", "")
    # Agent 6 is an extreme outlier
    await db.save_score(6, "0x600", 100, 100, 100, 100, 100, "TRUST", "", "", agent_identity=95)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    outliers = [a for a in r.json()["anomalies"] if a["type"] == "score_outlier"]
    assert len(outliers) >= 1
    outlier_ids = [o["agent_id"] for o in outliers]
    assert 6 in outlier_ids


@pytest.mark.asyncio
async def test_no_outlier_with_few_agents():
    """Outlier detection requires 5+ agents — skip if fewer."""
    await db.save_score(1, "0xa", 50, 50, 50, 50, 50, "CAUTION", "", "")
    await db.save_score(2, "0xb", 100, 100, 100, 100, 100, "TRUST", "", "", agent_identity=95)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    outliers = [a for a in r.json()["anomalies"] if a["type"] == "score_outlier"]
    assert len(outliers) == 0


# ─── Toxic Neighborhood ───

@pytest.mark.asyncio
async def test_toxic_neighborhood_detected():
    """Agent with contagion_adjustment <= -10 triggers toxic_neighborhood."""
    await db.save_score(1, "0xa", 40, 50, 50, 50, 50, "CAUTION", "", "",
                        agent_identity=30, contagion_adjustment=-15)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    toxic = [a for a in r.json()["anomalies"] if a["type"] == "toxic_neighborhood"]
    assert len(toxic) == 1
    assert toxic[0]["severity"] == "HIGH"


# ─── Query Params: limit and severity ───

@pytest.mark.asyncio
async def test_limit_param():
    """?limit=N caps the number of returned anomalies."""
    # Create multiple anomalies via sybil cluster + suspicious scores
    await db.save_score(1, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(2, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(3, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies?limit=2")
    data = r.json()
    assert len(data["anomalies"]) <= 2
    assert data["returned"] <= 2
    assert data["total"] >= data["returned"]


@pytest.mark.asyncio
async def test_severity_filter():
    """?severity=HIGH returns only HIGH severity anomalies."""
    # Agent with contagion = HIGH, suspicious_high_score = MEDIUM
    await db.save_score(1, "0xa", 75, 10, 80, 80, 80, "TRUST", "", "",
                        contagion_adjustment=-15)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies?severity=HIGH")
    data = r.json()
    for a in data["anomalies"]:
        assert a["severity"] == "HIGH"


@pytest.mark.asyncio
async def test_severity_filter_case_insensitive():
    """?severity=high should work the same as ?severity=HIGH."""
    await db.save_score(1, "0xa", 40, 50, 50, 50, 50, "CAUTION", "", "",
                        contagion_adjustment=-15)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies?severity=high")
    data = r.json()
    for a in data["anomalies"]:
        assert a["severity"] == "HIGH"


# ─── Response Structure ───

@pytest.mark.asyncio
async def test_response_structure():
    """Verify response shape includes total, returned, checked, limit, offset."""
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    data = r.json()
    assert "anomalies" in data
    assert "total" in data
    assert "returned" in data
    assert "checked" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 50  # default
    assert data["offset"] == 0  # default
    assert isinstance(data["anomalies"], list)


@pytest.mark.asyncio
async def test_empty_db_returns_empty_anomalies():
    """No agents scored = no anomalies."""
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    data = r.json()
    assert data["total"] == 0
    assert data["checked"] == 0
    assert data["anomalies"] == []


@pytest.mark.asyncio
async def test_anomalies_sorted_by_severity():
    """HIGH severity anomalies should appear before MEDIUM ones."""
    # HIGH: contagion, MEDIUM: suspicious_high_score
    await db.save_score(1, "0xa", 75, 10, 80, 80, 80, "TRUST", "", "",
                        contagion_adjustment=-15)
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    anomalies = r.json()["anomalies"]
    if len(anomalies) >= 2:
        severities = [a["severity"] for a in anomalies]
        high_indices = [i for i, s in enumerate(severities) if s == "HIGH"]
        medium_indices = [i for i, s in enumerate(severities) if s == "MEDIUM"]
        if high_indices and medium_indices:
            assert max(high_indices) < min(medium_indices)


# ─── Unit Tests for _detect_anomalies ───

@pytest.mark.asyncio
async def test_detect_anomalies_pure_function():
    """Test the detection logic directly without HTTP."""
    scores = [
        {"agent_id": 1, "trust_score": 100, "activity": 10, "longevity": 10,
         "contagion_adjustment": 0, "sybil_flagged": 0},
        {"agent_id": 2, "trust_score": 50, "activity": 50, "longevity": 50,
         "contagion_adjustment": -20, "sybil_flagged": 0},
    ]
    history_map = {1: [], 2: []}
    wallet_map = {}
    threats = []

    anomalies = _detect_anomalies(scores, history_map, wallet_map, threats)

    types = [a["type"] for a in anomalies]
    assert "suspicious_perfect_score" in types  # agent 1: score=100, low activity
    assert "toxic_neighborhood" in types  # agent 2: contagion=-20


@pytest.mark.asyncio
async def test_detect_anomalies_sybil_from_threats():
    """Recent SYBIL_CLUSTER threats should appear as anomalies."""
    scores = [
        {"agent_id": 1, "trust_score": 50, "activity": 50, "longevity": 50,
         "contagion_adjustment": 0, "sybil_flagged": 0},
    ]
    recent_threats = [
        {"threat_type": "SYBIL_CLUSTER", "agent_id": 99,
         "details": "Cluster of 5 agents detected"},
    ]
    anomalies = _detect_anomalies(scores, {1: []}, {}, recent_threats)
    sybil_threats = [a for a in anomalies if a["type"] == "sybil_cluster_detected"]
    assert len(sybil_threats) == 1
    assert sybil_threats[0]["agent_id"] == 99


# ─── Pagination (offset) ───

@pytest.mark.asyncio
async def test_offset_param():
    """?offset=N skips the first N anomalies."""
    # Create a sybil cluster (3 agents = 1 sybil_cluster anomaly)
    # plus suspicious_high_score for each (longevity < 20 and trust >= 70)
    await db.save_score(1, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(2, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(3, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r_all = await client.get("/api/anomalies?limit=500")
        total = r_all.json()["total"]
        # Now fetch with offset=2
        r_page = await client.get(f"/api/anomalies?offset=2&limit=500")
    data = r_page.json()
    assert data["offset"] == 2
    assert data["total"] == total
    assert data["returned"] == max(total - 2, 0)


@pytest.mark.asyncio
async def test_offset_and_limit_combined():
    """?offset=1&limit=1 returns exactly one anomaly from the middle."""
    await db.save_score(1, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(2, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    await db.save_score(3, "0xSAME", 100, 10, 10, 80, 80, "TRUST", "", "")
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies?offset=1&limit=1")
    data = r.json()
    assert data["returned"] == 1
    assert data["offset"] == 1
    assert data["limit"] == 1


@pytest.mark.asyncio
async def test_default_limit_is_50():
    """Default limit should be 50 when not specified."""
    async with AsyncClient(transport=_transport(), base_url="http://test") as client:
        r = await client.get("/api/anomalies")
    data = r.json()
    assert data["limit"] == 50
    assert data["offset"] == 0
