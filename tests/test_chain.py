import pytest
import time
from unittest.mock import AsyncMock
from agent.chain import ChainFetcher, WalletData


@pytest.mark.asyncio
async def test_fetch_wallet_data_combines_chains():
    fetcher = ChainFetcher.__new__(ChainFetcher)
    fetcher.base_rpc = "https://mock-base"
    fetcher.eth_rpc = "https://mock-eth"
    fetcher._fetch_chain = AsyncMock(side_effect=[
        {"tx_count": 50, "first_tx_timestamp": 1700000000, "contracts": ["0xa"], "counterparties": {"0xb"}, "active_days": 10, "total_days": 30},
        {"tx_count": 100, "first_tx_timestamp": 1690000000, "contracts": ["0xc"], "counterparties": {"0xd"}, "active_days": 20, "total_days": 60},
    ])
    data = await fetcher.fetch_wallet("0xabc")
    assert data.tx_count == 150
    assert len(data.counterparties) == 2


def test_wallet_data_age_days():
    data = WalletData(
        tx_count=10,
        first_tx_timestamp=int(time.time()) - 86400 * 30,
        contracts=[], counterparties=set(),
        malicious_contracts=0, verified_counterparties=0,
        flagged_counterparties=0, unverified_contracts=0,
        active_days=10, total_days=30,
    )
    assert 29 <= data.wallet_age_days <= 31
