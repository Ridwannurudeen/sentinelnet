import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from api import app, db, _fire_webhooks, _deliver_webhook, VALID_WEBHOOK_EVENTS


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    db.path = ":memory:"
    await db.init()
    yield
    await db.close()


# ─── Registration ───


@pytest.mark.asyncio
async def test_register_webhook():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
            "events": ["score_update", "verdict_changed"],
        })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "registered"
    assert data["url"] == "https://example.com/hook"
    assert "score_update" in data["events"]
    assert data["webhook_id"].startswith("wh_")


@pytest.mark.asyncio
async def test_register_webhook_defaults_all_events():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
        })
    assert r.status_code == 200
    assert set(r.json()["events"]) == set(VALID_WEBHOOK_EVENTS)


@pytest.mark.asyncio
async def test_register_webhook_rejects_invalid_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/webhooks", json={"url": "not-a-url"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_register_webhook_rejects_private_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/webhooks", json={"url": "http://127.0.0.1/hook"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_register_webhook_rejects_invalid_event():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
            "events": ["not_real_event"],
        })
    assert r.status_code == 400


# ─── List ───


@pytest.mark.asyncio
async def test_list_webhooks_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/webhooks")
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["webhooks"] == []


@pytest.mark.asyncio
async def test_list_webhooks_after_register():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/webhooks", json={"url": "https://a.com/h1"})
        await client.post("/api/webhooks", json={"url": "https://b.com/h2"})
        r = await client.get("/api/webhooks")
    assert r.status_code == 200
    assert r.json()["total"] == 2


# ─── Delete ───


@pytest.mark.asyncio
async def test_delete_webhook():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/webhooks", json={"url": "https://a.com/h"})
        wh_id = reg.json()["webhook_id"]
        r = await client.delete(f"/api/webhooks/{wh_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_webhook_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.delete("/api/webhooks/wh_nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_from_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/webhooks", json={"url": "https://a.com/h"})
        wh_id = reg.json()["webhook_id"]
        await client.delete(f"/api/webhooks/{wh_id}")
        r = await client.get("/api/webhooks")
    assert r.json()["total"] == 0


# ─── Persistence ───


@pytest.mark.asyncio
async def test_webhooks_persisted_in_db():
    """Webhooks stored in SQLite, not just in-memory."""
    await db.save_webhook("wh_test1", "https://example.com/h", ["score_update"])
    webhooks = await db.get_webhooks()
    assert len(webhooks) == 1
    assert webhooks[0]["id"] == "wh_test1"
    assert webhooks[0]["url"] == "https://example.com/h"
    assert webhooks[0]["events"] == ["score_update"]


@pytest.mark.asyncio
async def test_db_delete_webhook():
    await db.save_webhook("wh_del", "https://example.com/h", ["score_update"])
    deleted = await db.delete_webhook("wh_del")
    assert deleted is True
    deleted_again = await db.delete_webhook("wh_del")
    assert deleted_again is False


@pytest.mark.asyncio
async def test_db_count_webhooks():
    assert await db.count_webhooks() == 0
    await db.save_webhook("wh_c1", "https://a.com/h", ["score_update"])
    await db.save_webhook("wh_c2", "https://b.com/h", ["score_update"])
    assert await db.count_webhooks() == 2


# ─── Delivery + Retry ───


@pytest.mark.asyncio
async def test_deliver_webhook_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.httpx.AsyncClient", return_value=mock_client):
        result = await _deliver_webhook("https://example.com/h", {"test": True})
    assert result is True
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_deliver_webhook_retries_on_500():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await _deliver_webhook("https://example.com/h", {"test": True}, max_retries=3)
    assert result is False
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_deliver_webhook_no_retry_on_4xx():
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("api.httpx.AsyncClient", return_value=mock_client):
        result = await _deliver_webhook("https://example.com/h", {"test": True})
    assert result is False
    mock_client.post.assert_called_once()


# ─── Event Detection ───


@pytest.mark.asyncio
async def test_fire_webhooks_verdict_changed():
    """Webhook subscribed to verdict_changed fires when verdict differs."""
    await db.save_webhook("wh_vc", "https://example.com/h", ["verdict_changed"])

    with patch("api._deliver_webhook", new_callable=AsyncMock, return_value=True) as mock_deliver:
        await _fire_webhooks("score_update", {
            "agent_id": 1,
            "trust_score": 30,
            "verdict": "REJECT",
            "previous_score": 80,
            "previous_verdict": "TRUST",
        })
    mock_deliver.assert_called_once()
    payload = mock_deliver.call_args[0][1]
    assert "verdict_changed" in payload["triggered_events"]


@pytest.mark.asyncio
async def test_fire_webhooks_trust_degraded():
    """Webhook subscribed to trust_degraded fires when score drops."""
    await db.save_webhook("wh_td", "https://example.com/h", ["trust_degraded"])

    with patch("api._deliver_webhook", new_callable=AsyncMock, return_value=True) as mock_deliver:
        await _fire_webhooks("score_update", {
            "agent_id": 1,
            "trust_score": 40,
            "verdict": "SUSPECT",
            "previous_score": 80,
            "previous_verdict": "TRUST",
        })
    mock_deliver.assert_called_once()
    payload = mock_deliver.call_args[0][1]
    assert "trust_degraded" in payload["triggered_events"]


@pytest.mark.asyncio
async def test_fire_webhooks_sybil_detected():
    """Webhook subscribed to sybil_detected fires when sybil_flagged is True."""
    await db.save_webhook("wh_sd", "https://example.com/h", ["sybil_detected"])

    with patch("api._deliver_webhook", new_callable=AsyncMock, return_value=True) as mock_deliver:
        await _fire_webhooks("score_update", {
            "agent_id": 1,
            "trust_score": 20,
            "verdict": "REJECT",
            "previous_score": 80,
            "previous_verdict": "TRUST",
            "sybil_flagged": True,
        })
    mock_deliver.assert_called_once()
    payload = mock_deliver.call_args[0][1]
    assert "sybil_detected" in payload["triggered_events"]


@pytest.mark.asyncio
async def test_fire_webhooks_no_match_skips():
    """Webhook subscribed to sybil_detected does NOT fire on plain score_update."""
    await db.save_webhook("wh_no", "https://example.com/h", ["sybil_detected"])

    with patch("api._deliver_webhook", new_callable=AsyncMock) as mock_deliver:
        await _fire_webhooks("score_update", {
            "agent_id": 1,
            "trust_score": 80,
            "verdict": "TRUST",
            "previous_score": 75,
            "previous_verdict": "TRUST",
            "sybil_flagged": False,
        })
    mock_deliver.assert_not_called()


@pytest.mark.asyncio
async def test_fire_webhooks_score_update_subscriber():
    """Webhook subscribed to score_update fires on any score change."""
    await db.save_webhook("wh_su", "https://example.com/h", ["score_update"])

    with patch("api._deliver_webhook", new_callable=AsyncMock, return_value=True) as mock_deliver:
        await _fire_webhooks("score_update", {
            "agent_id": 1,
            "trust_score": 85,
            "verdict": "TRUST",
            "previous_score": 80,
            "previous_verdict": "TRUST",
        })
    mock_deliver.assert_called_once()


@pytest.mark.asyncio
async def test_fire_webhooks_no_webhooks_registered():
    """No error when firing with zero webhooks."""
    with patch("api._deliver_webhook", new_callable=AsyncMock) as mock_deliver:
        await _fire_webhooks("score_update", {"agent_id": 1, "trust_score": 80, "verdict": "TRUST"})
    mock_deliver.assert_not_called()
