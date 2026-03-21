# tests/test_config.py
from config import Settings

def test_settings_defaults():
    s = Settings(
        BASE_RPC_URL="https://mainnet.base.org",
        ETH_RPC_URL="https://eth.llamarpc.com",
        IDENTITY_REGISTRY="0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        SENTINELNET_AGENT_ID=31253,
        PRIVATE_KEY="0x" + "ab" * 32,
    )
    assert s.SWEEP_INTERVAL_SECONDS == 1800
    assert s.STAKE_AMOUNT_ETH == 0.001
    assert s.RESCORE_AFTER_HOURS == 24

def test_settings_has_defaults():
    s = Settings()
    assert s.BASE_RPC_URL == "https://mainnet.base.org"
    assert s.REPUTATION_REGISTRY == "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
