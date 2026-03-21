# tests/test_discovery.py
"""Tests for the progressive discovery sweep."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
from agent.discovery import Discovery, BATCH_SIZE, STALE_CAP


@pytest.mark.asyncio
async def test_find_new_agents_progressive():
    erc8004 = AsyncMock()
    erc8004.get_total_agents = AsyncMock(return_value=35000)
    db = AsyncMock()
    db.get_all_scores = AsyncMock(return_value=[])
    d = Discovery(erc8004, db, AsyncMock(), self_agent_id=31253)

    agents = await d.find_new_agents()
    assert len(agents) <= BATCH_SIZE
    assert 31253 not in agents
    # Cursor should have advanced
    assert d._scan_cursor > 1


@pytest.mark.asyncio
async def test_cursor_advances():
    erc8004 = AsyncMock()
    erc8004.get_total_agents = AsyncMock(return_value=35000)
    db = AsyncMock()
    db.get_all_scores = AsyncMock(return_value=[])
    d = Discovery(erc8004, db, AsyncMock(), self_agent_id=31253)

    await d.find_new_agents()
    cursor1 = d._scan_cursor
    await d.find_new_agents()
    cursor2 = d._scan_cursor
    assert cursor2 > cursor1


@pytest.mark.asyncio
async def test_skips_already_scored():
    erc8004 = AsyncMock()
    erc8004.get_total_agents = AsyncMock(return_value=500)
    db = AsyncMock()
    db.get_all_scores = AsyncMock(return_value=[
        {"agent_id": i, "scored_at": "2026-03-20T00:00:00+00:00"} for i in range(1, 51)
    ])
    d = Discovery(erc8004, db, AsyncMock(), self_agent_id=31253)

    agents = await d.find_new_agents()
    for aid in range(1, 51):
        assert aid not in agents


@pytest.mark.asyncio
async def test_find_stale_agents():
    db = AsyncMock()
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db.get_all_scores = AsyncMock(return_value=[
        {"agent_id": 1, "scored_at": "2026-01-01T00:00:00+00:00"},
        {"agent_id": 2, "scored_at": recent},
    ])
    d = Discovery(AsyncMock(), db, AsyncMock(), self_agent_id=31253)

    stale = await d.find_stale_agents()
    assert 1 in stale
    assert 2 not in stale


@pytest.mark.asyncio
async def test_stale_agents_capped():
    db = AsyncMock()
    db.get_all_scores = AsyncMock(return_value=[
        {"agent_id": i, "scored_at": "2026-03-01T00:00:00+00:00"} for i in range(1, 201)
    ])
    d = Discovery(AsyncMock(), db, AsyncMock(), self_agent_id=31253)

    stale = await d.find_stale_agents()
    assert len(stale) <= STALE_CAP
