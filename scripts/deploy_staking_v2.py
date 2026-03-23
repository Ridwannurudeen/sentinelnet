"""
Deploy SentinelNetStaking v2 via direct EOA transaction.
Adds smart account as authorized caller alongside the sentinel EOA.
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

PRIVATE_KEY = os.environ["PRIVATE_KEY"]
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
SMART_ACCOUNT = os.environ.get("CDP_SMART_ACCOUNT", "0x6663BeB922ab00A545c7b2c01986C6a5f275AaB9")


def main():
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    account = Account.from_key(PRIVATE_KEY)
    print(f"Deployer/Sentinel: {account.address}")
    print(f"Smart Account:     {SMART_ACCOUNT}")
    print(f"Balance:           {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

    # Load compiled artifact
    artifact_path = os.path.join(os.path.dirname(__file__), "..",
                                  "contracts", "artifacts", "contracts",
                                  "SentinelNetStaking.sol", "SentinelNetStaking.json")
    if not os.path.exists(artifact_path):
        # Try VPS path
        artifact_path = "/opt/sentinelnet/contracts/artifacts/contracts/SentinelNetStaking.sol/SentinelNetStaking.json"

    with open(artifact_path) as f:
        artifact = json.load(f)

    # Build contract
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])

    # Constructor args: sentinel (EOA) + smartAccount
    constructor_tx = contract.constructor(account.address, SMART_ACCOUNT).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "gasPrice": int(w3.eth.gas_price * 1.1),
        "chainId": 8453,
    })

    # Estimate gas
    gas = w3.eth.estimate_gas(constructor_tx)
    constructor_tx["gas"] = int(gas * 1.15)
    cost = w3.from_wei(constructor_tx["gas"] * constructor_tx["gasPrice"], "ether")
    print(f"Estimated gas: {constructor_tx['gas']} (~{cost} ETH)")

    # Sign and send
    signed = w3.eth.account.sign_transaction(constructor_tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx sent: https://basescan.org/tx/{tx_hash.hex()}")

    # Wait for receipt
    print("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_addr = receipt["contractAddress"]
    print(f"\nSentinelNetStaking v2 deployed at: {contract_addr}")
    print(f"BaseScan: https://basescan.org/address/{contract_addr}")
    print(f"\nUpdate .env:")
    print(f"STAKING_CONTRACT={contract_addr}")


if __name__ == "__main__":
    main()
