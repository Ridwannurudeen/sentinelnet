# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RPC (single URL — kept for backwards compat)
    BASE_RPC_URL: str = "https://mainnet.base.org"
    ETH_RPC_URL: str = "https://eth.llamarpc.com"

    # Multi-RPC failover (comma-separated, takes priority over single URL above)
    BASE_RPC_URLS: str = "https://base.drpc.org,https://base.publicnode.com,https://base.llamarpc.com,https://mainnet.base.org"
    ETH_RPC_URLS: str = "https://ethereum-rpc.publicnode.com,https://eth.drpc.org,https://cloudflare-eth.com/v1/mainnet,https://eth.llamarpc.com"

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
    STAKING_CONTRACT: str = "0xEe1A8f34F1320D534b9a547f882762EABCB4f96d"

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
    ADMIN_KEY: str = ""  # Admin key for scoring/management endpoints

    class Config:
        env_file = ".env"
