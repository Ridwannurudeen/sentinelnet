"""Push trust scores on-chain via TrustGate.batchUpdateTrust() (direct EOA, no paymaster).

Required env (read from .env or process env):
    PRIVATE_KEY, TRUSTGATE_CONTRACT
Optional env:
    BASE_RPC_URL (default: https://mainnet.base.org)
"""
import json
import os

from dotenv import load_dotenv
import requests
from web3 import Web3

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
CONTRACT = _require("TRUSTGATE_CONTRACT")
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

with open("/opt/sentinelnet/contracts/artifacts/contracts/TrustGate.sol/TrustGate.json") as f:
    abi = json.load(f)["abi"]
contract = w3.eth.contract(address=CONTRACT, abi=abi)

bal = w3.eth.get_balance(account.address)
gas_price = w3.eth.gas_price
print(f"Sender: {account.address}")
print(f"Balance: {w3.from_wei(bal, 'ether')} ETH")
print(f"Gas price: {w3.from_wei(gas_price, 'gwei')} gwei")

sentinel_id = int(os.environ.get("SENTINELNET_AGENT_ID", "31253"))
ids_to_score = list(range(1, 21)) + [sentinel_id]
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
    print(f"  Agent {aid}: score={score}, verdict={info['verdict']}")

print(f"\nPushing {len(agent_ids)} scores on-chain...")

nonce = w3.eth.get_transaction_count(account.address)
tx = contract.functions.batchUpdateTrust(agent_ids, scores, uris).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gasPrice": gas_price,
    "chainId": 8453,
})

gas_est = w3.eth.estimate_gas(tx)
tx["gas"] = int(gas_est * 1.3)
cost = gas_est * gas_price
print(f"Gas estimate: {gas_est} (~{w3.from_wei(cost, 'ether'):.10f} ETH)")

if cost > bal:
    raise SystemExit("INSUFFICIENT FUNDS")

signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx sent: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")
print(f"Gas used: {receipt.gasUsed}")
print(f"Block: {receipt.blockNumber}")
print(f"BaseScan: https://basescan.org/tx/{tx_hash.hex()}")
