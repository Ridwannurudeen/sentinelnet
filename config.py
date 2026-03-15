# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RPC
    BASE_RPC_URL: str
    ETH_RPC_URL: str = "https://eth.llamarpc.com"

    # ERC-8004
    IDENTITY_REGISTRY: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    REPUTATION_REGISTRY: str = ""
    VALIDATION_REGISTRY: str = ""
    SENTINELNET_AGENT_ID: int = 31253

    # Wallet
    PRIVATE_KEY: str = ""

    # IPFS
    PINATA_API_KEY: str = ""
    PINATA_SECRET_KEY: str = ""

    # Staking
    STAKE_AMOUNT_ETH: float = 0.001

    # Sweep
    SWEEP_INTERVAL_SECONDS: int = 1800
    RESCORE_AFTER_HOURS: int = 24

    class Config:
        env_file = ".env"
