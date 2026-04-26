"""Push all scored agents on-chain in batches via CDP paymaster.

Required env (read from .env or process env):
    PRIVATE_KEY, CDP_API_KEY_ID, CDP_API_SECRET, CDP_SMART_ACCOUNT,
    CDP_PAYMASTER_URL, TRUSTGATE_CONTRACT
Optional env:
    BASE_RPC_URL (default: https://mainnet.base.org)
    BATCH_SIZE   (default: 50)
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
load_dotenv()


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
CONTRACT = _require("TRUSTGATE_CONTRACT")
NETWORK = "base"
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))

with open("/opt/sentinelnet/contracts/artifacts/contracts/TrustGate.sol/TrustGate.json") as f:
    abi = json.load(f)["abi"]


async def main():
    local_account = Account.from_key(PRIVATE_KEY)
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    contract = w3.eth.contract(address=CONTRACT, abi=abi)

    print("Fetching all scores from API...")
    resp = requests.get("http://localhost:8004/api/scores?apply_decay=true")
    data = resp.json()
    all_scores = data["scores"]
    print(f"Total scored: {len(all_scores)}")

    sentinel_id = int(os.environ.get("SENTINELNET_AGENT_ID", "31253"))
    already_pushed = set(range(1, 21)) | {sentinel_id}
    to_push = [s for s in all_scores if s["agent_id"] not in already_pushed]
    print(f"New to push: {len(to_push)}")

    async with CdpClient(api_key_id=API_KEY_ID, api_key_secret=API_SECRET) as client:
        smart = await client.evm.get_smart_account(address=SMART_ACCOUNT, owner=local_account)

        pushed = 0
        errors = 0
        for i in range(0, len(to_push), BATCH_SIZE):
            batch = to_push[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            agent_ids = [a["agent_id"] for a in batch]
            scores = [min(max(int(a["trust_score"]), 0), 100) for a in batch]
            uris = [a.get("evidence_uri", "") or "" for a in batch]

            calldata = contract.functions.batchUpdateTrust(
                agent_ids, scores, uris
            )._encode_transaction_data()

            call = EncodedCall(to=CONTRACT, value=Web3.to_wei(0, "ether"), data=calldata)

            print(f"Batch {batch_num}: {len(agent_ids)} agents...", end=" ", flush=True)
            try:
                result = await client.evm.send_user_operation(
                    smart_account=smart, calls=[call],
                    network=NETWORK, paymaster_url=PAYMASTER_URL,
                )
                print(f"OK ({result.status})")
                pushed += len(agent_ids)
                time.sleep(2)
            except Exception as e:
                err_msg = str(e)[:80]
                print(f"FAIL: {err_msg}")
                errors += 1
                if errors > 5:
                    print("Too many errors, stopping.")
                    break
                time.sleep(5)

        print("\n=== DONE ===")
        print(f"Pushed: {pushed} agents on-chain")
        print(f"Errors: {errors}")
        print(f"Total on-chain: {pushed + 21} (including initial 21)")


if __name__ == "__main__":
    asyncio.run(main())
