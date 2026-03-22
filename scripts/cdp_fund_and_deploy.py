"""
Fund wallet via Coinbase CDP and deploy TrustGate.sol to Base Mainnet.
Usage: CDP_API_KEY_ID=... CDP_API_KEY_SECRET=... python3 scripts/cdp_fund_and_deploy.py
"""
import asyncio
import json
import os
import sys

from cdp import CdpClient


NETWORK = "base-mainnet"

TRUSTGATE_ARTIFACT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "contracts", "artifacts",
    "contracts", "TrustGate.sol", "TrustGate.json"
)


def load_artifact():
    real = os.path.realpath(TRUSTGATE_ARTIFACT)
    if not os.path.exists(real):
        raise FileNotFoundError(f"TrustGate artifact not found at {real}. Run 'npx hardhat compile' in contracts/")
    with open(real) as f:
        data = json.load(f)
    return data["abi"], data["bytecode"]


async def main():
    api_key_id = os.environ.get("CDP_API_KEY_ID", "")
    api_key_secret = os.environ.get("CDP_API_KEY_SECRET", "")

    if not api_key_id or not api_key_secret:
        print("ERROR: Set CDP_API_KEY_ID and CDP_API_KEY_SECRET env vars")
        sys.exit(1)

    abi, bytecode = load_artifact()
    print(f"Loaded TrustGate artifact ({len(bytecode)} bytes bytecode)")

    async with CdpClient(api_key_id=api_key_id, api_key_secret=api_key_secret) as client:
        # Create a server-managed account
        print("Creating CDP server account...")
        account = await client.evm.create_account()
        address = account.address
        print(f"Account address: {address}")

        # Check balance
        balances = await account.list_token_balances(NETWORK)
        print(f"Token balances: {balances}")

        # Request faucet (only works on testnets, but try anyway)
        try:
            print("Requesting faucet...")
            tx_hash = await account.request_faucet(NETWORK, "eth")
            print(f"Faucet tx: {tx_hash}")
        except Exception as e:
            print(f"Faucet not available on mainnet (expected): {e}")

        # For mainnet: need to transfer from existing funded wallet
        # or use the account.transfer() method
        print(f"\nTo deploy TrustGate, send >= 0.003 ETH (Base) to: {address}")
        print("Then re-run with DEPLOY=1 to deploy the contract.")
        print()

        # Save account info
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdp_account.json")
        with open(save_path, "w") as f:
            json.dump({"address": address}, f)
        print(f"Account saved to {save_path}")

        # If DEPLOY flag is set and account has balance, deploy
        if os.environ.get("DEPLOY") == "1":
            print("\nDeploying TrustGate...")

            # Build deploy transaction
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

            # Encode constructor (no args for TrustGate)
            contract = w3.eth.contract(abi=abi, bytecode=bytecode)
            deploy_data = contract.constructor().build_transaction({
                "from": address,
                "nonce": w3.eth.get_transaction_count(address),
                "gasPrice": w3.eth.gas_price,
                "chainId": 8453,
            })

            # Estimate gas
            gas_estimate = w3.eth.estimate_gas(deploy_data)
            deploy_data["gas"] = int(gas_estimate * 1.2)
            print(f"Estimated gas: {gas_estimate} (~{w3.from_wei(gas_estimate * w3.eth.gas_price, 'ether'):.6f} ETH)")

            # Send via CDP
            from cdp import TransactionRequestEIP1559
            tx = TransactionRequestEIP1559(
                to=None,  # contract creation
                value=hex(0),
                data=deploy_data["data"],
                gas=hex(deploy_data["gas"]),
                max_fee_per_gas=hex(w3.eth.gas_price * 2),
                max_priority_fee_per_gas=hex(w3.eth.max_priority_fee),
                nonce=hex(deploy_data["nonce"]),
                chain_id=hex(8453),
            )

            tx_hash = await account.send_transaction(transaction=tx, network=NETWORK)
            print(f"Deploy tx: {tx_hash}")
            print(f"View on BaseScan: https://basescan.org/tx/{tx_hash}")

            # Wait for receipt
            import time
            for _ in range(60):
                try:
                    receipt = w3.eth.get_transaction_receipt(tx_hash)
                    if receipt:
                        contract_address = receipt["contractAddress"]
                        print(f"\nTrustGate deployed to: {contract_address}")
                        print(f"Sentinel (owner): {address}")
                        print(f"\nAdd to .env on VPS:")
                        print(f"TRUSTGATE_CONTRACT={contract_address}")
                        print(f"\nBaseScan: https://basescan.org/address/{contract_address}")
                        return
                except Exception:
                    pass
                time.sleep(2)
            print("Timeout waiting for receipt. Check tx hash on BaseScan.")


if __name__ == "__main__":
    asyncio.run(main())
