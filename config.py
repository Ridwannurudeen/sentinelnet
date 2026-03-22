# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RPC
    BASE_RPC_URL: str = "https://mainnet.base.org"
    ETH_RPC_URL: str = "https://eth.llamarpc.com"

    # ERC-8004
    IDENTITY_REGISTRY: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    REPUTATION_REGISTRY: str = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
    VALIDATION_REGISTRY: str = ""
    SENTINELNET_AGENT_ID: int = 31253

    # Wallet
    PRIVATE_KEY: str = ""

    # Block explorer APIs
    BASESCAN_API_KEY: str = ""
    ETHERSCAN_API_KEY: str = ""

    # IPFS
    PINATA_API_KEY: str = ""
    PINATA_SECRET_KEY: str = ""
    PINATA_JWT: str = ""
    LIGHTHOUSE_API_KEY: str = ""

    # Staking
    STAKE_AMOUNT_ETH: float = 0.001
    STAKING_CONTRACT: str = "0xABEB1fa61b0b3B271D1E1E102289579251ABd6F7"

    # TrustGate on-chain oracle
    TRUSTGATE_CONTRACT: str = ""

    # Sweep
    SWEEP_INTERVAL_SECONDS: int = 1800
    RESCORE_AFTER_HOURS: int = 24

    # EAS (Ethereum Attestation Service)
    EAS_SCHEMA_UID: str = ""

    # Coinbase CDP Paymaster (gasless transactions)
    CDP_API_KEY_ID: str = ""
    CDP_API_SECRET: str = ""
    CDP_SMART_ACCOUNT: str = ""
    CDP_PAYMASTER_URL: str = ""

    # API Key Authentication
    API_KEYS: str = ""  # Comma-separated valid API keys

    class Config:
        env_file = ".env"
