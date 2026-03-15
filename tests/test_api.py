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


@pytest.mark.asyncio
async def test_trust_endpoint_404_for_unknown():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/trust/99999")
    assert r.status_code == 404
