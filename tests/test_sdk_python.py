# tests/test_sdk_python.py
"""Tests for the Python SDK client (uses mock server)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from api import app, db

# Import SDK
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))
from sentinelnet import SentinelNet, AsyncSentinelNet


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    db.path = ":memory:"
    await db.init()
    await db.save_score(1, "0xa", 80, 80, 80, 80, 80, "TRUST", "", "", agent_identity=75)
    await db.save_score(2, "0xb", 30, 30, 30, 30, 30, "REJECT", "", "", agent_identity=20)
    yield
    await db.close()


def test_sdk_badge_url():
    sn = SentinelNet(base_url="http://test")
    assert sn.badge_url(42) == "http://test/badge/42.svg"


@pytest.mark.asyncio
async def test_async_sdk_get_trust():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        score = await sn.get_trust(1)
        assert score["verdict"] in ("TRUST", "CAUTION", "REJECT")
        assert score["agent_id"] == 1


@pytest.mark.asyncio
async def test_async_sdk_is_trusted():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        assert await sn.is_trusted(1) is True
        assert await sn.is_trusted(2) is False


@pytest.mark.asyncio
async def test_async_sdk_trust_gate():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        assert await sn.trust_gate(1, min_score=55) is True
        assert await sn.trust_gate(2, min_score=55) is False


@pytest.mark.asyncio
async def test_async_sdk_batch():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        result = await sn.batch_trust([1, 2, 999])
        assert result["queried"] == 3
        assert result["found"] == 2


@pytest.mark.asyncio
async def test_async_sdk_stats():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        stats = await sn.get_stats()
        assert stats["agents_scored"] == 2


@pytest.mark.asyncio
async def test_async_sdk_threats():
    transport = ASGITransport(app=app)
    async with AsyncSentinelNet(base_url="http://test") as sn:
        sn._client = AsyncClient(transport=transport, base_url="http://test")
        threats = await sn.get_threats(limit=5)
        assert "threats" in threats
