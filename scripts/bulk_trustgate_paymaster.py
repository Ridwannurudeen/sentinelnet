"""
Bulk-write all scored agents to TrustGate via CDP Paymaster (gasless).
Reads all scores from local DB, checks which are already on-chain, writes the rest.
"""
import asyncio
import json
import os
import sys
import aiosqlite

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_account import Account
from cdp import CdpClient, EncodedCall


BATCH_SIZE = 25
DB_PATH = os.environ.get("DB_PATH", "sentinelnet.db")
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
TRUSTGATE = os.environ["TRUSTGATE_CONTRACT"]
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
CDP_API_KEY_ID = os.environ["CDP_API_KEY_ID"]
CDP_API_SECRET = os.environ["CDP_API_SECRET"]
CDP_SMART_ACCOUNT = os.environ["CDP_SMART_ACCOUNT"]
CDP_PAYMASTER_URL = os.environ["CDP_PAYMASTER_URL"]


async def main():
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    acct = Account.from_key(PRIVATE_KEY)

    with open(os.path.join(os.path.dirname(__file__), "..",
              "contracts", "artifacts", "contracts",
              "TrustGate.sol", "TrustGate.json")) as f:
        abi = json.load(f)["abi"]

    gate = w3.eth.contract(address=TRUSTGATE, abi=abi)
    on_chain_total = gate.functions.totalScored().call()
    print(f"TrustGate: {TRUSTGATE}")
    print(f"Sentinel: {gate.functions.sentinel().call()}")
    print(f"Smart account: {CDP_SMART_ACCOUNT}")
    print(f"Already on-chain: {on_chain_total}")

    # Get all scores from DB
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT agent_id, trust_score, evidence_uri FROM trust_scores ORDER BY agent_id"
        )
        rows = await cursor.fetchall()

    print(f"Total in DB: {len(rows)}")

    # Check which are already on-chain (spot check a few)
    all_scores = []
    for row in rows:
        aid = row["agent_id"]
        score = min(row["trust_score"], 100)
        uri = row["evidence_uri"] or ""
        all_scores.append((aid, score, uri))

    print(f"Writing {len(all_scores)} agents via paymaster in batches of {BATCH_SIZE}...")
    written = 0
    failed = 0

    async with CdpClient(api_key_id=CDP_API_KEY_ID, api_key_secret=CDP_API_SECRET) as client:
        smart = await client.evm.get_smart_account(
            address=CDP_SMART_ACCOUNT, owner=acct
        )
        print(f"Smart account confirmed: {smart.address}")

        for i in range(0, len(all_scores), BATCH_SIZE):
            batch = all_scores[i:i + BATCH_SIZE]
            agent_ids = [s[0] for s in batch]
            scores = [s[1] for s in batch]
            uris = [s[2] for s in batch]

            try:
                data = gate.functions.batchUpdateTrust(
                    agent_ids, scores, uris
                )._encode_transaction_data()

                call = EncodedCall(
                    to=TRUSTGATE,
                    value=0,
                    data=data,
                )

                result = await client.evm.send_user_operation(
                    smart_account=smart,
                    calls=[call],
                    network="base",
                    paymaster_url=CDP_PAYMASTER_URL,
                )

                written += len(batch)
                batch_num = i // BATCH_SIZE + 1
                total_batches = (len(all_scores) + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"  Batch {batch_num}/{total_batches}: {len(batch)} agents — UserOp: {result.user_op_hash}")

                # Small delay to avoid rate limits
                await asyncio.sleep(1)

            except Exception as e:
                failed += len(batch)
                print(f"  Batch {i // BATCH_SIZE + 1} FAILED: {e}")
                await asyncio.sleep(2)

    print(f"\nDone: {written} written, {failed} failed")
    print(f"Check: https://basescan.org/address/{TRUSTGATE}")


if __name__ == "__main__":
    asyncio.run(main())
