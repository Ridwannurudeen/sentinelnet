import pytest
from unittest.mock import AsyncMock
from agent.graph import TrustGraph


@pytest.mark.asyncio
async def test_get_neighborhood():
    db = AsyncMock()
    db.get_edges = AsyncMock(return_value=[
        {"counterparty": "0xabc", "interaction_count": 5, "is_flagged": 0},
        {"counterparty": "0xdef", "interaction_count": 3, "is_flagged": 1},
    ])
    graph = TrustGraph(db=db)
    result = await graph.get_neighborhood(42)
    assert result["agent_id"] == 42
    assert result["total_neighbors"] == 2
    assert result["neighbors"][0]["counterparty"] == "0xabc"
    assert result["neighbors"][1]["is_flagged"] is True


@pytest.mark.asyncio
async def test_empty_neighborhood():
    db = AsyncMock()
    db.get_edges = AsyncMock(return_value=[])
    graph = TrustGraph(db=db)
    result = await graph.get_neighborhood(999)
    assert result["total_neighbors"] == 0
    assert result["neighbors"] == []
