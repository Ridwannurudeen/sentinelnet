"""Test a single paymaster transaction to debug the failure."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


async def test():
    from cdp import CdpClient, EncodedCall
    from eth_account import Account
    from web3 import Web3

    api_key_id = os.getenv("CDP_API_KEY_ID")
    api_secret = os.getenv("CDP_API_SECRET")
    smart_account = os.getenv("CDP_SMART_ACCOUNT")
    paymaster_url = os.getenv("CDP_PAYMASTER_URL")
    private_key = os.getenv("PRIVATE_KEY")

    print(f"API Key: {api_key_id[:8]}...")
    print(f"Smart Account: {smart_account}")
    print(f"Paymaster: {paymaster_url[:60]}...")

    local_account = Account.from_key(private_key)
    print(f"EOA: {local_account.address}")

    w3 = Web3()
    rep_abi = [{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"int128","name":"value","type":"int128"},{"internalType":"uint8","name":"valueDecimals","type":"uint8"},{"internalType":"string","name":"tag1","type":"string"},{"internalType":"string","name":"tag2","type":"string"},{"internalType":"string","name":"endpoint","type":"string"},{"internalType":"string","name":"feedbackURI","type":"string"},{"internalType":"bytes32","name":"feedbackHash","type":"bytes32"}],"name":"giveFeedback","outputs":[],"stateMutability":"nonpayable","type":"function"}]

    rep = w3.eth.contract(address="0x8004BAa17C55a88189AE136b182e5fdA19dE9b63", abi=rep_abi)
    data = rep.encode_abi(
        abi_element_identifier="giveFeedback",
        args=[31253, 90, 0, "reliability", "sentinelnet-v2", "",
              "https://sentinelnet.gudman.xyz", b'\x00' * 32]
    )

    async with CdpClient(api_key_id=api_key_id, api_key_secret=api_secret) as client:
        smart = await client.evm.get_smart_account(
            address=smart_account, owner=local_account
        )
        print(f"Smart Account OK: {smart.address}")

        try:
            result = await client.evm.send_user_operation(
                smart_account=smart,
                calls=[EncodedCall(
                    to="0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
                    value=0,
                    data=data
                )],
                network="base",
                paymaster_url=paymaster_url,
            )
            print(f"SUCCESS! UserOp: {result.user_op_hash}")
            print(f"Status: {result.status}")
        except Exception as e:
            print(f"FAILED: {e}")
            # Check if it's a paymaster-specific error
            err_str = str(e)
            if "insufficient balance" in err_str:
                print("\nDiagnosis: Paymaster is NOT sponsoring the transaction.")
                print("The bundler is checking sender balance instead of paymaster deposit.")
                print("Possible causes:")
                print("  1. Paymaster policy has changed (check CDP Dashboard)")
                print("  2. Paymaster credits exhausted for this project")
                print("  3. Rate limit hit on paymaster endpoint")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
