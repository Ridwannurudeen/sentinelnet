"""
Deploy TrustGate.sol via Coinbase Smart Account + Paymaster (zero gas cost).
v2: passes sentinel address as constructor argument.
"""
import asyncio
import json
import sys

# Remove nest_asyncio interference
if "nest_asyncio" in sys.modules:
    del sys.modules["nest_asyncio"]

import os
from dotenv import load_dotenv
from cdp import CdpClient, EncodedCall
from eth_account import Account
from web3 import Web3

load_dotenv()

PRIVATE_KEY = os.environ["PRIVATE_KEY"]
API_KEY_ID = os.environ["CDP_API_KEY_ID"]
API_SECRET = os.environ["CDP_API_SECRET"]
NETWORK = "base"
PAYMASTER_URL = os.environ["CDP_PAYMASTER_URL"]
CREATE2_FACTORY = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
SMART_ACCOUNT = os.environ.get("CDP_SMART_ACCOUNT", "0x7c0A6aAb54B511C85A4B9D5E05D40f45e7BaAb78")

# Derive sentinel address from the private key
SENTINEL_ADDRESS = Account.from_key(PRIVATE_KEY).address

with open("/opt/sentinelnet/contracts/artifacts/contracts/TrustGate.sol/TrustGate.json") as f:
    artifact = json.load(f)


async def deploy():
    local_account = Account.from_key(PRIVATE_KEY)
    print(f"Signer: {local_account.address}")

    async with CdpClient(api_key_id=API_KEY_ID, api_key_secret=API_SECRET) as client:
        smart = await client.evm.get_smart_account(address=SMART_ACCOUNT, owner=local_account)
        print(f"Smart account: {smart.address}")

        # Build init_code = bytecode + abi.encode(address)
        w3 = Web3()
        bytecode_hex = artifact["bytecode"].replace("0x", "")
        # Encode constructor arg: address padded to 32 bytes
        constructor_args = w3.codec.encode(["address"], [SENTINEL_ADDRESS]).hex()
        init_code = bytecode_hex + constructor_args

        # CREATE2: salt (32 bytes) + init_code
        salt = "00" * 32
        create2_data = "0x" + salt + init_code

        call = EncodedCall(
            to=CREATE2_FACTORY,
            value=Web3.to_wei(0, "ether"),
            data=create2_data,
        )

        print(f"Sentinel will be: {SENTINEL_ADDRESS}")
        print(f"Deploying via paymaster...")
        result = await client.evm.send_user_operation(
            smart_account=smart,
            calls=[call],
            network=NETWORK,
            paymaster_url=PAYMASTER_URL,
        )
        print(f"UserOp hash: {result.user_op_hash}")
        print(f"Status: {result.status}")

        # Wait for confirmation
        print("Waiting for on-chain confirmation...")
        try:
            final = await client.evm.wait_for_user_operation(smart, NETWORK, result.user_op_hash)
            print(f"Final status: {final.status}")
            if hasattr(final, "transaction_hash") and final.transaction_hash:
                print(f"Tx: https://basescan.org/tx/{final.transaction_hash}")
        except Exception as e:
            print(f"Wait error (tx may still confirm): {e}")

        # Calculate CREATE2 address
        factory_bytes = bytes.fromhex(CREATE2_FACTORY[2:])
        salt_bytes = bytes(32)
        init_hash = w3.keccak(bytes.fromhex(init_code))
        raw = b"\xff" + factory_bytes + salt_bytes + init_hash
        contract_addr = Web3.to_checksum_address(w3.keccak(raw)[12:].hex())
        print(f"\nTrustGate deployed at: {contract_addr}")
        print(f"Sentinel (owner): {SENTINEL_ADDRESS}")
        print(f"BaseScan: https://basescan.org/address/{contract_addr}")
        print(f"\nAdd to .env:")
        print(f"TRUSTGATE_CONTRACT={contract_addr}")


asyncio.run(deploy())
