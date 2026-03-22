"""
Fund wallet via Coinbase CDP and deploy TrustGate.sol to Base Mainnet.
Usage: python scripts/cdp_fund_and_deploy.py
"""
import asyncio
import json
import os
import sys

from cdp import Cdp, Wallet


CDP_API_KEY_NAME = os.environ.get("CDP_API_KEY_NAME", "")
CDP_API_KEY_PRIVATE_KEY = os.environ.get("CDP_API_KEY_PRIVATE_KEY", "")

# TrustGate compiled bytecode and ABI path
TRUSTGATE_ARTIFACT = os.path.join(
    os.path.dirname(__file__), "..", "contracts", "artifacts", "contracts",
    "TrustGate.sol", "TrustGate.json"
)


def load_artifact():
    # Try hardhat artifact first
    paths = [
        TRUSTGATE_ARTIFACT,
        os.path.join(os.path.dirname(__file__), "..", "contracts", "artifacts",
                     "TrustGate.sol", "TrustGate.json"),
    ]
    for p in paths:
        real = os.path.realpath(p)
        if os.path.exists(real):
            with open(real) as f:
                data = json.load(f)
            return data["abi"], data["bytecode"]
    raise FileNotFoundError(f"TrustGate artifact not found. Run 'npx hardhat compile' in contracts/ first.\nTried: {paths}")


def main():
    if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE_KEY:
        print("ERROR: Set CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY env vars")
        sys.exit(1)

    # Configure CDP
    Cdp.configure(CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY)
    print("CDP configured")

    # Create wallet on Base mainnet
    print("Creating wallet on Base mainnet...")
    wallet = Wallet.create(network_id="base-mainnet")
    print(f"Wallet address: {wallet.default_address}")

    # Check balance
    balance = wallet.balance("eth")
    print(f"ETH balance: {balance}")

    if float(balance) < 0.001:
        print("\nWallet needs funding. Options:")
        print(f"  1. Send ETH to {wallet.default_address} on Base")
        print("  2. Use wallet.fund() for Coinbase onramp")
        print("\nAttempting wallet.fund()...")
        try:
            fund_op = wallet.fund(amount=0.005, asset_id="eth")
            fund_op.wait()
            print(f"Funded! New balance: {wallet.balance('eth')}")
        except Exception as e:
            print(f"Fund failed: {e}")
            print(f"\nManually send >= 0.003 ETH to: {wallet.default_address}")
            print("Then re-run this script.")

            # Save wallet for later
            wallet_data = wallet.export_data()
            save_path = os.path.join(os.path.dirname(__file__), "wallet_data.json")
            with open(save_path, "w") as f:
                json.dump({"wallet_id": wallet_data.wallet_id, "seed": wallet_data.seed}, f)
            print(f"Wallet saved to {save_path}")
            return

    # Deploy TrustGate
    print("\nLoading TrustGate artifact...")
    abi, bytecode = load_artifact()

    print("Deploying TrustGate to Base mainnet...")
    deployed = wallet.deploy_contract(
        abi=abi,
        bytecode=bytecode,
        constructor_args={},
    )
    deployed.wait()

    contract_address = deployed.contract_address
    print(f"\nTrustGate deployed to: {contract_address}")
    print(f"Sentinel (owner): {wallet.default_address}")
    print(f"\nAdd to .env on VPS:")
    print(f"TRUSTGATE_CONTRACT={contract_address}")


if __name__ == "__main__":
    main()
