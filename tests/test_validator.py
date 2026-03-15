import pytest
from unittest.mock import AsyncMock
from agent.validator import Validator
from agent.trust_engine import TrustResult


@pytest.mark.asyncio
async def test_handle_validation_request():
    mock_result = TrustResult(
        trust_score=75, verdict="TRUST",
        longevity=80, activity=70, counterparty=85, contract_risk=60,
    )
    pipeline = AsyncMock(return_value=mock_result)
    erc8004 = AsyncMock()
    erc8004.validation_response = AsyncMock(return_value="0xtx123")
    publisher = AsyncMock()
    publisher.publish = AsyncMock(return_value={"evidence_uri": "ipfs://test"})

    validator = Validator(erc8004=erc8004, pipeline=pipeline, publisher=publisher)
    result = await validator.handle_validation_request(b"\x00" * 32, agent_id=42)

    assert result["trust_score"] == 75
    assert result["verdict"] == "TRUST"
    assert result["validation_tx"] == "0xtx123"


@pytest.mark.asyncio
async def test_handle_validation_request_unknown_agent():
    pipeline = AsyncMock(return_value=None)
    erc8004 = AsyncMock()
    publisher = AsyncMock()

    validator = Validator(erc8004=erc8004, pipeline=pipeline, publisher=publisher)
    result = await validator.handle_validation_request(b"\x00" * 32, agent_id=999)
    assert "error" in result
