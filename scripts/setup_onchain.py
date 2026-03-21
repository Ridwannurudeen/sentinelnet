#!/usr/bin/env python3
"""One-time on-chain setup: register EAS schema for SentinelNet trust attestations."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from config import Settings
from agent.eas import EASAttestor


async def main():
    settings = Settings()

    if not settings.PRIVATE_KEY:
        print("ERROR: PRIVATE_KEY not set in .env")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
    print(f"Connected to Base: {w3.is_connected()}")

    attestor = EASAttestor(w3=w3, private_key=settings.PRIVATE_KEY)
    print(f"Registering EAS schema from: {attestor.account.address}")

    schema_uid = await attestor.register_schema()
    if schema_uid:
        print(f"\nSchema registered successfully!")
        print(f"Schema UID: {schema_uid}")
        print(f"\nAdd to .env:")
        print(f"EAS_SCHEMA_UID={schema_uid}")
    else:
        print("Schema registration failed. Check logs.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
