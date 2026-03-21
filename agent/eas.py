"""EAS (Ethereum Attestation Service) integration for trust attestations on Base.

Every trust score becomes a verifiable on-chain attestation.
EAS on Base: 0x4200000000000000000000000000000000000021
SchemaRegistry: 0x4200000000000000000000000000000000000020
"""
import asyncio
import json
import logging
from eth_abi import encode
from web3 import Web3

logger = logging.getLogger(__name__)

EAS_ADDRESS = "0x4200000000000000000000000000000000000021"
SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"

# Schema: uint256 agentId, uint8 trustScore, string verdict, string evidenceURI, bool sybilFlagged
TRUST_SCHEMA = "uint256 agentId, uint8 trustScore, string verdict, string evidenceURI, bool sybilFlagged"

EAS_ABI = json.loads('[{"inputs":[{"components":[{"internalType":"bytes32","name":"schema","type":"bytes32"},{"components":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint64","name":"expirationTime","type":"uint64"},{"internalType":"bool","name":"revocable","type":"bool"},{"internalType":"bytes32","name":"refUID","type":"bytes32"},{"internalType":"bytes","name":"data","type":"bytes"},{"internalType":"uint256","name":"value","type":"uint256"}],"internalType":"struct AttestationRequestData","name":"data","type":"tuple"}],"internalType":"struct AttestationRequest","name":"request","type":"tuple"}],"name":"attest","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"payable","type":"function"}]')

SCHEMA_REGISTRY_ABI = json.loads('[{"inputs":[{"internalType":"string","name":"schema","type":"string"},{"internalType":"contract ISchemaResolver","name":"resolver","type":"address"},{"internalType":"bool","name":"revocable","type":"bool"}],"name":"register","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"nonpayable","type":"function"}]')


class EASAttestor:
    def __init__(self, w3: Web3, private_key: str, schema_uid: str = ""):
        self.w3 = w3
        self.private_key = private_key
        self.account = w3.eth.account.from_key(private_key) if private_key else None
        self.schema_uid = schema_uid
        self.eas = w3.eth.contract(
            address=Web3.to_checksum_address(EAS_ADDRESS),
            abi=EAS_ABI,
        )
        self.schema_registry = w3.eth.contract(
            address=Web3.to_checksum_address(SCHEMA_REGISTRY),
            abi=SCHEMA_REGISTRY_ABI,
        )

    async def register_schema(self) -> str:
        """Register the trust score schema on EAS. Returns schema UID."""
        if not self.account:
            return ""
        try:
            nonce = await asyncio.to_thread(
                self.w3.eth.get_transaction_count, self.account.address
            )
            tx = self.schema_registry.functions.register(
                TRUST_SCHEMA,
                "0x0000000000000000000000000000000000000000",  # no resolver
                True,  # revocable
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 300000,
                "maxFeePerGas": self.w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt, tx_hash, timeout=30
            )
            # Schema UID is in the logs
            schema_uid = receipt.logs[0].topics[1].hex() if receipt.logs else ""
            self.schema_uid = schema_uid
            logger.info(f"EAS schema registered: {schema_uid}")
            return schema_uid
        except Exception as e:
            logger.error(f"Schema registration failed: {e}")
            return ""

    async def attest_trust(self, agent_id: int, trust_score: int,
                           verdict: str, evidence_uri: str,
                           wallet: str, sybil_flagged: bool = False) -> str:
        """Create an on-chain trust attestation for an agent. Returns attestation UID."""
        if not self.account or not self.schema_uid:
            return ""
        try:
            # Encode attestation data
            data = encode(
                ["uint256", "uint8", "string", "string", "bool"],
                [agent_id, min(trust_score, 255), verdict, evidence_uri, sybil_flagged]
            )

            recipient = Web3.to_checksum_address(wallet) if wallet else "0x0000000000000000000000000000000000000000"
            schema_bytes = bytes.fromhex(self.schema_uid.replace("0x", ""))
            if len(schema_bytes) < 32:
                schema_bytes = schema_bytes.ljust(32, b'\x00')

            nonce = await asyncio.to_thread(
                self.w3.eth.get_transaction_count, self.account.address
            )

            attestation_request = (
                schema_bytes,
                (
                    recipient,
                    0,          # no expiration
                    True,       # revocable
                    b'\x00' * 32,  # no ref UID
                    data,
                    0,          # no value
                )
            )

            tx = self.eas.functions.attest(attestation_request).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 400000,
                "maxFeePerGas": self.w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"EAS attestation sent for agent {agent_id}: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.warning(f"EAS attestation failed for agent {agent_id}: {e}")
            return ""
