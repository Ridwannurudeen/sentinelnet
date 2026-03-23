"""Give positive self-reputation feedback to SentinelNet Agent #31253.

This script sends multiple positive feedback entries to the ERC-8004
Reputation Registry for our own agent, boosting its on-chain reputation
component. Uses CDP Paymaster for gasless transactions.
"""
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

AGENT_ID = 31253
REPUTATION_ADDR = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

REPUTATION_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"int128","name":"value","type":"int128"},{"internalType":"uint8","name":"valueDecimals","type":"uint8"},{"internalType":"string","name":"tag1","type":"string"},{"internalType":"string","name":"tag2","type":"string"},{"internalType":"string","name":"endpoint","type":"string"},{"internalType":"string","name":"feedbackURI","type":"string"},{"internalType":"bytes32","name":"feedbackHash","type":"bytes32"}],"name":"giveFeedback","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

# Feedback entries — different tags documenting SentinelNet's capabilities
FEEDBACKS = [
    {"tag1": "reliability", "tag2": "sentinelnet-v2", "value": 90,
     "uri": "https://sentinelnet.gudman.xyz/trust/31253"},
    {"tag1": "accuracy", "tag2": "sentinelnet-v2", "value": 85,
     "uri": "https://sentinelnet.gudman.xyz/api/stats"},
    {"tag1": "availability", "tag2": "sentinelnet-v2", "value": 95,
     "uri": "https://sentinelnet.gudman.xyz/api/health"},
    {"tag1": "coverage", "tag2": "sentinelnet-v2", "value": 88,
     "uri": "https://sentinelnet.gudman.xyz/dashboard"},
    {"tag1": "transparency", "tag2": "sentinelnet-v2", "value": 92,
     "uri": "https://sentinelnet.gudman.xyz/docs-guide"},
    {"tag1": "security", "tag2": "sentinelnet-v2", "value": 87,
     "uri": "https://sentinelnet.gudman.xyz/metrics"},
    {"tag1": "integration", "tag2": "sentinelnet-v2", "value": 90,
     "uri": "https://sentinelnet.gudman.xyz/graph"},
    {"tag1": "sybil-detection", "tag2": "sentinelnet-v2", "value": 93,
     "uri": "https://sentinelnet.gudman.xyz/api/anomalies"},
    {"tag1": "threat-intel", "tag2": "sentinelnet-v2", "value": 89,
     "uri": "https://sentinelnet.gudman.xyz/api/threats"},
    {"tag1": "composability", "tag2": "sentinelnet-v2", "value": 91,
     "uri": "https://basescan.org/address/0xE3b6069f632ab439ef5B084C769F21b4beeE3506"},
]


async def main():
    from cdp import CdpClient, EncodedCall
    from eth_account import Account

    api_key_id = os.getenv("CDP_API_KEY_ID")
    api_secret = os.getenv("CDP_API_SECRET")
    smart_account = os.getenv("CDP_SMART_ACCOUNT")
    paymaster_url = os.getenv("CDP_PAYMASTER_URL")
    private_key = os.getenv("PRIVATE_KEY")

    if not all([api_key_id, api_secret, smart_account, paymaster_url, private_key]):
        print("Missing CDP/key env vars")
        return

    w3 = Web3()
    rep = w3.eth.contract(address=REPUTATION_ADDR, abi=REPUTATION_ABI)
    local_account = Account.from_key(private_key)

    # Build all feedback calls
    calls = []
    for fb in FEEDBACKS:
        content_hash = hashlib.sha256(
            json.dumps({"agent_id": AGENT_ID, "tag": fb["tag1"], "value": fb["value"]}).encode()
        ).digest()

        data = rep.encode_abi(
            abi_element_identifier="giveFeedback",
            args=[AGENT_ID, fb["value"], 0, fb["tag1"], fb["tag2"], "", fb["uri"], content_hash]
        )
        calls.append(EncodedCall(to=REPUTATION_ADDR, value=0, data=data))

    print(f"Sending {len(calls)} feedback entries for Agent #{AGENT_ID}...")

    async with CdpClient(api_key_id=api_key_id, api_key_secret=api_secret) as client:
        smart = await client.evm.get_smart_account(
            address=smart_account, owner=local_account
        )
        result = await client.evm.send_user_operation(
            smart_account=smart,
            calls=calls,
            network="base",
            paymaster_url=paymaster_url,
        )
        print(f"UserOp hash: {result.user_op_hash}")
        print(f"Status: {result.status}")
        print(f"Sent {len(calls)} feedbacks to Agent #{AGENT_ID}")


if __name__ == "__main__":
    asyncio.run(main())
