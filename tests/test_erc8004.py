from agent.erc8004 import ERC8004Client


def test_parse_agent_uri():
    client = ERC8004Client.__new__(ERC8004Client)
    registration = client._parse_registration_json('{"name":"TestAgent","services":[],"active":true}')
    assert registration["name"] == "TestAgent"
    assert registration["active"] is True


def test_build_feedback_params():
    client = ERC8004Client.__new__(ERC8004Client)
    params = client._build_feedback_params(
        agent_id=42, value=73, tag1="trustScore",
        tag2="sentinelnet-v1", feedback_uri="ipfs://abc", feedback_hash=b"\x00" * 32
    )
    assert params["agent_id"] == 42
    assert params["value"] == 73
    assert params["tag1"] == "trustScore"
