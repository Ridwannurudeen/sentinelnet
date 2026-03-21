import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from api import app, db


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    db.path = ":memory:"
    await db.init()
    yield
    await db.close()


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "sentinelnet"
    assert r.json()["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_trust_endpoint_404_for_unknown():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_scores_endpoint_includes_verdicts():
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    await db.save_score(2, "0xb", 30, 30, 30, 30, 30, "REJECT", "", "", agent_identity=20)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/scores?apply_decay=false")
    data = r.json()
    assert data["total"] == 2
    assert data["verdicts"]["TRUST"] >= 1
    assert "sybil_flagged" in data


@pytest.mark.asyncio
async def test_stats_endpoint():
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/stats")
    data = r.json()
    assert data["agents_scored"] == 1
    assert "sybil_flagged" in data
    assert "stale_scores" in data


@pytest.mark.asyncio
async def test_trust_history_endpoint():
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    await db.save_score(1, "0xa", 70, 70, 70, 70, 70, "TRUST", "", "", agent_identity=60)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/1/history")
    data = r.json()
    assert data["entries"] == 2


@pytest.mark.asyncio
async def test_trust_history_404_for_unknown():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/99999/history")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trust_graph_endpoint():
    await db.save_edge(1, "0xdef", 3, False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/graph/1")
    data = r.json()
    assert data["total_neighbors"] == 1


@pytest.mark.asyncio
async def test_score_decay_applied():
    # Save a score with old timestamp
    await db.save_score(1, "0xa", 90, 90, 90, 90, 90, "TRUST", "", "", agent_identity=90)
    # Manually set scored_at to 30 days ago
    import datetime
    old_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()
    await db.conn.execute("UPDATE trust_scores SET scored_at = ? WHERE agent_id = 1", (old_date,))
    await db.conn.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/1")
    data = r.json()
    # After 30 days decay: 90 * e^(-0.01*30) ≈ 67
    assert data["trust_score"] < 90
    assert data["trust_score_raw"] == 90
    assert data["is_stale"] is True
