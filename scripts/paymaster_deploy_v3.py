"""
Deploy TrustGate v3 via CDP smart account + push initial scores.
All on-chain calls go through the paymaster (zero EOA gas).

Required env (read from .env or process env):
    PRIVATE_KEY              owner EOA for the smart account
    CDP_API_KEY_ID
    CDP_API_SECRET
    CDP_SMART_ACCOUNT        already-deployed CDP smart account address
    CDP_PAYMASTER_URL
    BASE_RPC_URL             (defaults to https://mainnet.base.org)

Usage:
    /opt/sentinelnet/venv/bin/python scripts/paymaster_deploy_v3.py
"""
import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv

if "nest_asyncio" in sys.modules:
    del sys.modules["nest_asyncio"]

from cdp import CdpClient, EncodedCall
from eth_account import Account
from web3 import Web3
import requests

load_dotenv("/opt/sentinelnet/.env")
load_dotenv()  # also pick up local .env if present

CREATE2_FACTORY = "0x4e59b44847b379578588920cA78FbF26c0B4956C"


def _require(env_var: str) -> str:
    val = os.environ.get(env_var, "").strip()
    if not val:
        raise SystemExit(
            f"Missing env var {env_var}. Set it in /opt/sentinelnet/.env (see script header)."
        )
    return val


PRIVATE_KEY = _require("PRIVATE_KEY")
API_KEY_ID = _require("CDP_API_KEY_ID")
API_SECRET = _require("CDP_API_SECRET")
SMART_ACCOUNT = _require("CDP_SMART_ACCOUNT")
PAYMASTER_URL = _require("CDP_PAYMASTER_URL")
NETWORK = "base"
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

with open("/opt/sentinelnet/contracts/artifacts/contracts/TrustGate.sol/TrustGate.json") as f:
    artifact = json.load(f)


async def main():
    local_account = Account.from_key(PRIVATE_KEY)
    w3 = Web3()

    async with CdpClient(api_key_id=API_KEY_ID, api_key_secret=API_SECRET) as client:
        smart = await client.evm.get_smart_account(address=SMART_ACCOUNT, owner=local_account)
        print(f"Smart account: {smart.address}")

        # ── Step 1: Deploy with smart account as sentinel ──
        bytecode_hex = artifact["bytecode"].replace("0x", "")
        constructor_args = w3.codec.encode(["address"], [SMART_ACCOUNT]).hex()
        init_code = bytecode_hex + constructor_args

        salt = "00" * 31 + "01"
        create2_data = "0x" + salt + init_code

        deploy_call = EncodedCall(
            to=CREATE2_FACTORY,
            value=Web3.to_wei(0, "ether"),
            data=create2_data,
        )

        print(f"Deploying TrustGate (sentinel={SMART_ACCOUNT})...")
        result = await client.evm.send_user_operation(
            smart_account=smart,
            calls=[deploy_call],
            network=NETWORK,
            paymaster_url=PAYMASTER_URL,
        )
        print(f"Deploy UserOp: {result.user_op_hash}")
        print(f"Status: {result.status}")

        # Calculate CREATE2 address
        factory_bytes = bytes.fromhex(CREATE2_FACTORY[2:])
        salt_bytes = bytes.fromhex(salt)
        init_hash = w3.keccak(bytes.fromhex(init_code))
        raw = b"\xff" + factory_bytes + salt_bytes + init_hash
        contract_addr = Web3.to_checksum_address(w3.keccak(raw)[12:].hex())
        print(f"Predicted address: {contract_addr}")

        w3_rpc = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        print("Waiting for deploy confirmation...")
        for _ in range(30):
            time.sleep(3)
            code = w3_rpc.eth.get_code(contract_addr)
            if len(code) > 0:
                print(f"Contract confirmed! Code: {len(code)} bytes")
                slot0 = w3_rpc.eth.get_storage_at(contract_addr, 0)
                sentinel = "0x" + slot0.hex()[-40:]
                print(f"Sentinel: {Web3.to_checksum_address(sentinel)}")
                break
        else:
            print("Timeout - check BaseScan")
            return

        # ── Step 2: Push trust scores on-chain via paymaster ──
        print("\nFetching trust scores from API...")
        ids_to_score = list(range(1, 21)) + [int(os.environ.get("SENTINELNET_AGENT_ID", "31253"))]
        resp = requests.post("http://localhost:8004/trust/batch", json={"agent_ids": ids_to_score})
        data = resp.json()["results"]

        agent_ids = []
        scores = []
        uris = []
        for aid_str, info in data.items():
            aid = int(aid_str)
            score = min(max(int(info["trust_score"]), 0), 100)
            uri = info.get("evidence_uri", "")
            agent_ids.append(aid)
            scores.append(score)
            uris.append(uri)
            print(f"  Agent {aid}: score={score} ({info['verdict']})")

        contract_obj = w3_rpc.eth.contract(address=contract_addr, abi=artifact["abi"])
        calldata = contract_obj.functions.batchUpdateTrust(agent_ids, scores, uris)._encode_transaction_data()

        update_call = EncodedCall(
            to=contract_addr,
            value=Web3.to_wei(0, "ether"),
            data=calldata,
        )

        print(f"\nPushing {len(agent_ids)} scores on-chain via paymaster...")
        result2 = await client.evm.send_user_operation(
            smart_account=smart,
            calls=[update_call],
            network=NETWORK,
            paymaster_url=PAYMASTER_URL,
        )
        print(f"Update UserOp: {result2.user_op_hash}")
        print(f"Status: {result2.status}")

        time.sleep(10)
        total = contract_obj.functions.totalScored().call()
        print(f"\nOn-chain totalScored: {total}")
        record = contract_obj.functions.getTrustRecord(int(os.environ.get("SENTINELNET_AGENT_ID", "31253"))).call()
        print(f"Self agent on-chain: score={record[0]}, verdict={record[1]}, time={record[2]}")

        print("\n=== RESULTS ===")
        print(f"TrustGate: {contract_addr}")
        print(f"Sentinel: {SMART_ACCOUNT}")
        print(f"Scores pushed: {len(agent_ids)}")
        print(f"BaseScan: https://basescan.org/address/{contract_addr}")
        print(f"\nTRUSTGATE_CONTRACT={contract_addr}")


if __name__ == "__main__":
    asyncio.run(main())
