#!/usr/bin/env python3
"""Register a new ERC-8004 agent from the current wallet and set a spec-compliant agentURI.

Two-step process:
  1. register() — mints a new agent NFT, returns the agentId
  2. setAgentURI(agentId, dataURI) — sets the base64-encoded registration JSON

Optionally:
  3. setAgentWallet(agentId, wallet, deadline, signature) — proves wallet ownership via EIP-712

Usage:
    python scripts/register_new_agent.py              # dry-run (shows JSON + gas estimates)
    python scripts/register_new_agent.py --execute     # actually sends transactions
    python scripts/register_new_agent.py --update-uri  # only update URI for existing agent
"""
import argparse
import asyncio
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from eth_account.messages import encode_typed_data
from config import Settings

IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

# Full ABI for Identity Registry (register, setAgentURI, setAgentWallet)
IDENTITY_ABI = json.loads("""[
    {
        "inputs": [],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "string", "name": "newURI", "type": "string"}
        ],
        "name": "setAgentURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "address", "name": "newWallet", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"}
        ],
        "name": "setAgentWallet",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getAgentWallet",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"indexed": false, "internalType": "string", "name": "agentURI", "type": "string"},
            {"indexed": true, "internalType": "address", "name": "owner", "type": "address"}
        ],
        "name": "Registered",
        "type": "event"
    }
]""")


def build_registration_json(agent_id: int) -> dict:
    """Build ERC-8004 spec-compliant registration JSON."""
    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": "SentinelNet",
        "description": (
            "Autonomous agent reputation watchdog for ERC-8004 on Base. "
            "Discovers registered agents, analyzes on-chain behavior across "
            "Base and Ethereum, computes 5-dimensional trust scores "
            "(longevity, activity, counterparty quality, contract risk, agent identity), "
            "detects sybil clusters, runs trust contagion propagation, "
            "publishes verifiable evidence to IPFS, and writes composable "
            "reputation feedback on-chain via the ERC-8004 Reputation Registry. "
            "Scores are backed by ETH stakes with 72-hour challenge windows."
        ),
        "image": "https://sentinelnet.gudman.xyz/static/og-image.png",
        "services": [
            {
                "name": "web",
                "endpoint": "https://sentinelnet.gudman.xyz/dashboard"
            },
            {
                "name": "MCP",
                "endpoint": "https://sentinelnet.gudman.xyz/mcp",
                "version": "2025-06-18"
            },
            {
                "name": "REST API",
                "endpoint": "https://sentinelnet.gudman.xyz/api"
            }
        ],
        "x402Support": False,
        "active": True,
        "registrations": [
            {
                "agentId": agent_id,
                "agentRegistry": f"eip155:8453:{IDENTITY_REGISTRY}"
            }
        ],
        "supportedTrust": [
            "reputation"
        ]
    }


def to_data_uri(registration: dict) -> str:
    """Encode registration JSON as a base64 data URI for on-chain storage."""
    raw = json.dumps(registration, separators=(",", ":"))
    encoded = base64.b64encode(raw.encode()).decode()
    return f"data:application/json;base64,{encoded}"


def build_tx_params(w3: Web3, sender: str, nonce: int, gas: int) -> dict:
    """Build transaction parameters for Base mainnet."""
    return {
        "from": sender,
        "nonce": nonce,
        "gas": gas,
        "maxFeePerGas": w3.to_wei(0.15, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        "chainId": 8453,
    }


def sign_agent_wallet_eip712(w3: Web3, private_key: str, agent_id: int,
                              new_wallet: str, deadline: int) -> bytes:
    """Sign the EIP-712 typed data for setAgentWallet."""
    domain = {
        "name": "AgentRegistry",
        "version": "1",
        "chainId": 8453,
        "verifyingContract": IDENTITY_REGISTRY,
    }
    types = {
        "SetAgentWallet": [
            {"name": "agentId", "type": "uint256"},
            {"name": "newWallet", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ]
    }
    message = {
        "agentId": agent_id,
        "newWallet": new_wallet,
        "deadline": deadline,
    }
    signable = encode_typed_data(
        domain_data=domain,
        types=types,
        primary_type="SetAgentWallet",
        message_data=message,
    )
    signed = w3.eth.account.sign_message(signable, private_key=private_key)
    return signed.signature


async def main():
    parser = argparse.ArgumentParser(description="Register new ERC-8004 agent")
    parser.add_argument("--execute", action="store_true", help="Actually send transactions")
    parser.add_argument("--update-uri", action="store_true", help="Only update URI for existing agent (uses SENTINELNET_AGENT_ID from config)")
    parser.add_argument("--set-wallet", action="store_true", help="Also set agentWallet via EIP-712")
    args = parser.parse_args()

    settings = Settings()
    if not settings.PRIVATE_KEY:
        print("ERROR: PRIVATE_KEY not set in .env")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
    account = w3.eth.account.from_key(settings.PRIVATE_KEY)
    sender = account.address
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(IDENTITY_REGISTRY),
        abi=IDENTITY_ABI,
    )

    print(f"Connected to Base: {w3.is_connected()}")
    print(f"Sender: {sender}")
    balance = w3.eth.get_balance(sender)
    print(f"Balance: {w3.from_wei(balance, 'ether')} ETH")

    if args.update_uri:
        # --- Update URI only for existing agent ---
        agent_id = settings.SENTINELNET_AGENT_ID
        print(f"\n=== Updating URI for existing agent {agent_id} ===")

        owner = contract.functions.ownerOf(agent_id).call()
        if owner.lower() != sender.lower():
            print(f"ERROR: Agent {agent_id} owned by {owner}, not {sender}")
            sys.exit(1)

        registration = build_registration_json(agent_id)
        data_uri = to_data_uri(registration)

        print(f"\nRegistration JSON:")
        print(json.dumps(registration, indent=2))
        print(f"\nData URI length: {len(data_uri)} bytes")

        gas_estimate = w3.eth.estimate_gas({
            "to": IDENTITY_REGISTRY,
            "from": sender,
            "data": contract.functions.setAgentURI(agent_id, data_uri)
                .build_transaction(build_tx_params(w3, sender, 0, 500000))["data"],
        })
        print(f"setAgentURI gas estimate: {gas_estimate}")

        if not args.execute:
            print("\nDry run — add --execute to send transaction")
            return

        nonce = w3.eth.get_transaction_count(sender)
        tx = contract.functions.setAgentURI(agent_id, data_uri).build_transaction(
            build_tx_params(w3, sender, nonce, gas_estimate + 20000)
        )
        signed = w3.eth.account.sign_transaction(tx, settings.PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"setAgentURI tx: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")
        return

    # --- Full registration flow ---
    print("\n=== Step 1: Register new agent (empty URI) ===")

    gas_register = w3.eth.estimate_gas({
        "to": IDENTITY_REGISTRY,
        "from": sender,
        "data": contract.functions.register("")
            .build_transaction(build_tx_params(w3, sender, 0, 500000))["data"],
    })
    print(f"register() gas estimate: {gas_register}")

    if not args.execute:
        # Show what the registration would look like with a placeholder ID
        reg = build_registration_json(99999)
        print(f"\nSample registration JSON (agentId will be set after mint):")
        print(json.dumps(reg, indent=2))
        data_uri = to_data_uri(reg)
        print(f"\nData URI length: {len(data_uri)} bytes")
        print(f"\nEstimated total cost: ~{w3.from_wei(gas_register * w3.to_wei(0.15, 'gwei'), 'ether'):.8f} ETH (register) + URI update")
        print("\nDry run — add --execute to send transactions")
        return

    # Send register() transaction
    nonce = w3.eth.get_transaction_count(sender)
    tx = contract.functions.register("").build_transaction(
        build_tx_params(w3, sender, nonce, gas_register + 20000)
    )
    signed = w3.eth.account.sign_transaction(tx, settings.PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"register() tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        print("ERROR: register() transaction failed!")
        sys.exit(1)

    # Extract agentId from Registered event
    registered_events = contract.events.Registered().process_receipt(receipt)
    if registered_events:
        agent_id = registered_events[0]["args"]["agentId"]
    else:
        # Fallback: parse Transfer event for tokenId
        transfer_topic = w3.keccak(text="Transfer(address,address,uint256)")
        for log in receipt.logs:
            if log.topics and log.topics[0] == transfer_topic and len(log.topics) >= 4:
                agent_id = int(log.topics[3].hex(), 16)
                break
        else:
            print("ERROR: Could not extract agentId from receipt")
            print(f"Logs: {receipt.logs}")
            sys.exit(1)

    print(f"New agent ID: {agent_id}")

    # Step 2: Set the full registration URI
    print(f"\n=== Step 2: Set agentURI for agent {agent_id} ===")
    registration = build_registration_json(agent_id)
    data_uri = to_data_uri(registration)

    print(f"Registration JSON:")
    print(json.dumps(registration, indent=2))

    nonce += 1
    gas_uri = w3.eth.estimate_gas({
        "to": IDENTITY_REGISTRY,
        "from": sender,
        "data": contract.functions.setAgentURI(agent_id, data_uri)
            .build_transaction(build_tx_params(w3, sender, 0, 500000))["data"],
    })
    print(f"setAgentURI gas estimate: {gas_uri}")

    tx = contract.functions.setAgentURI(agent_id, data_uri).build_transaction(
        build_tx_params(w3, sender, nonce, gas_uri + 20000)
    )
    signed = w3.eth.account.sign_transaction(tx, settings.PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"setAgentURI tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")

    # Step 3: Set agentWallet via EIP-712 signature (optional)
    if args.set_wallet:
        print(f"\n=== Step 3: Set agentWallet for agent {agent_id} ===")
        deadline = int(time.time()) + 3600  # 1 hour from now
        try:
            signature = sign_agent_wallet_eip712(
                w3, settings.PRIVATE_KEY, agent_id, sender, deadline
            )
            nonce += 1
            tx = contract.functions.setAgentWallet(
                agent_id, sender, deadline, signature
            ).build_transaction(
                build_tx_params(w3, sender, nonce, 100000)
            )
            signed = w3.eth.account.sign_transaction(tx, settings.PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"setAgentWallet tx: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")
        except Exception as e:
            print(f"setAgentWallet failed (may need different EIP-712 domain): {e}")
            print("You can retry this step later once the domain params are confirmed.")

    # Summary
    print(f"\n{'='*60}")
    print(f"REGISTRATION COMPLETE")
    print(f"{'='*60}")
    print(f"Agent ID:     {agent_id}")
    print(f"Owner:        {sender}")
    print(f"Registry:     eip155:8453:{IDENTITY_REGISTRY}")
    print(f"Dashboard:    https://sentinelnet.gudman.xyz/dashboard")
    print(f"")
    print(f"Next steps:")
    print(f"  1. Update SENTINELNET_AGENT_ID={agent_id} in .env on VPS")
    print(f"  2. Restart sentinelnet.service")
    print(f"  3. Update agent.json with new agent ID")


if __name__ == "__main__":
    asyncio.run(main())
