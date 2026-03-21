import pytest
from unittest.mock import AsyncMock
from agent.publisher import Publisher


def test_build_evidence_json():
    pub = Publisher.__new__(Publisher)
    evidence = pub._build_evidence(
        agent_id=42, wallet="0xabc",
        trust_score=73, longevity=85, activity=68,
        counterparty=79, contract_risk=62, verdict="TRUST",
        chains=["base", "ethereum"], agent_identity=80,
    )
    assert evidence["agent_id"] == 42
    assert evidence["trust_score"] == 73
    assert "scored_at" in evidence
    assert evidence["scorer"] == "sentinelnet-v1"
    assert evidence["breakdown"]["agent_identity"] == 80


@pytest.mark.asyncio
async def test_pin_to_ipfs_returns_cid():
    pub = Publisher.__new__(Publisher)
    pub._http_post = AsyncMock(return_value={"IpfsHash": "QmTest123"})
    pub.pinata_api_key = "key"
    pub.pinata_secret_key = "secret"
    pub.pinata_jwt = ""
    cid = await pub.pin_json({"test": True})
    assert cid == "ipfs://QmTest123"
