"""
Deploy TrustGate.sol via Coinbase Smart Account + Paymaster (zero gas cost).
"""
import asyncio
import json
import sys

# Remove nest_asyncio interference
if "nest_asyncio" in sys.modules:
    del sys.modules["nest_asyncio"]

from cdp import CdpClient, EncodedCall
from cdp.evm_smart_account import EvmSmartAccount
from eth_account import Account
from web3 import Web3

PRIVATE_KEY = "0x5136fa1c0e8e05a3fa4df4254babb7e9a0cd0c3f1eeb91f9e4e5eafee6e535b4"
API_KEY_ID = "dc255f0a-8c42-45a8-8a64-5d8ff902f805"
API_SECRET = "d8v/vccs/MZ7Xpp7no8wzBV68KJ1p/VlIIKJquYlonyi5Aa3pW0rbiaRtg4JxphweYWwCS0r0jzrmREE84RqQw=="
NETWORK = "base"
PAYMASTER_URL = "https://api.developer.coinbase.com/rpc/v1/base/ZCvk3bSsElw4OBdTMQIDo32Fb7nAa5dC"
CREATE2_FACTORY = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
SMART_ACCOUNT = "0x6663BeB922ab00A545c7b2c01986C6a5f275AaB9"

with open("/opt/sentinelnet/contracts/artifacts/contracts/TrustGate.sol/TrustGate.json") as f:
    artifact = json.load(f)


async def deploy():
    local_account = Account.from_key(PRIVATE_KEY)
    print(f"Signer: {local_account.address}")

    async with CdpClient(api_key_id=API_KEY_ID, api_key_secret=API_SECRET) as client:
        # Get existing smart account, pass raw eth_account LocalAccount as owner
        smart = await client.evm.get_smart_account(address=SMART_ACCOUNT, owner=local_account)
        print(f"Smart account: {smart.address}")

        # CREATE2: salt (32 bytes) + init_code
        salt = "00" * 32
        init_code = artifact["bytecode"].replace("0x", "")
        create2_data = "0x" + salt + init_code

        call = EncodedCall(
            to=CREATE2_FACTORY,
            value=Web3.to_wei(0, "ether"),
            data=create2_data,
        )

        print(f"Deploying via paymaster...")
        print(f"Paymaster: {PAYMASTER_URL}")
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
        final = await client.evm.wait_for_user_operation(smart, NETWORK, result.user_op_hash)
        print(f"Final status: {final.status}")
        if hasattr(final, "transaction_hash") and final.transaction_hash:
            print(f"Tx: https://basescan.org/tx/{final.transaction_hash}")

        # Calculate CREATE2 address
        w3 = Web3()
        factory_bytes = bytes.fromhex(CREATE2_FACTORY[2:])
        salt_bytes = bytes(32)
        init_hash = w3.keccak(bytes.fromhex(init_code))
        raw = b"\xff" + factory_bytes + salt_bytes + init_hash
        contract_addr = Web3.to_checksum_address(w3.keccak(raw)[12:].hex())
        print(f"\nTrustGate deployed at: {contract_addr}")
        print(f"BaseScan: https://basescan.org/address/{contract_addr}")
        print(f"\nAdd to .env:")
        print(f"TRUSTGATE_CONTRACT={contract_addr}")


asyncio.run(deploy())
