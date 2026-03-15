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
    # agent_id 0 is not in range(1, 101), scored_ids has 0-94, self is 999
    # new = range(1..100) - {0..94} - {999} = {95,96,97,98,99,100}
    assert len(new_ids) == 6


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
