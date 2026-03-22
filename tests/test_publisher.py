import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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


@pytest.mark.asyncio
async def test_pin_to_lighthouse_returns_cid():
    pub = Publisher.__new__(Publisher)
    pub.lighthouse_api_key = "lh-test-key"

    mock_response = MagicMock()
    mock_response.json.return_value = {"Hash": "QmLighthouse456", "Name": "evidence.json", "Size": "123"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        cid = await pub.pin_json_lighthouse({"test": True})
    assert cid == "ipfs://QmLighthouse456"


@pytest.mark.asyncio
async def test_publish_falls_through_to_lighthouse():
    """When Pinata fails, publisher should try Lighthouse before self-hosted fallback."""
    pub = Publisher(
        pinata_api_key="key", pinata_secret_key="secret",
        pinata_jwt="", lighthouse_api_key="lh-key",
    )
    pub.pin_json = AsyncMock(side_effect=Exception("403 Forbidden"))

    mock_response = MagicMock()
    mock_response.json.return_value = {"Hash": "QmFallback789", "Name": "evidence.json", "Size": "99"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await pub.publish(
            agent_id=42, wallet="0xabc", trust_score=73,
            longevity=85, activity=68, counterparty=79,
            contract_risk=62, verdict="TRUST",
        )
    assert result["evidence_uri"] == "ipfs://QmFallback789"
    pub.pin_json.assert_called_once()


@pytest.mark.asyncio
async def test_publish_all_ipfs_fail_uses_self_hosted():
    """When both Pinata and Lighthouse fail, fall back to self-hosted URI."""
    pub = Publisher(
        pinata_api_key="key", pinata_secret_key="secret",
        pinata_jwt="", lighthouse_api_key="lh-key",
    )
    pub.pin_json = AsyncMock(side_effect=Exception("403 Forbidden"))
    pub.pin_json_lighthouse = AsyncMock(side_effect=Exception("500 Server Error"))

    result = await pub.publish(
        agent_id=42, wallet="0xabc", trust_score=73,
        longevity=85, activity=68, counterparty=79,
        contract_risk=62, verdict="TRUST",
    )
    assert result["evidence_uri"].startswith("https://sentinelnet.gudman.xyz/evidence/42")
    pub.pin_json.assert_called_once()
    pub.pin_json_lighthouse.assert_called_once()
