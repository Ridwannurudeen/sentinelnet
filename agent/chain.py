import time
from dataclasses import dataclass, field
from typing import Set, List


@dataclass
class WalletData:
    tx_count: int
    first_tx_timestamp: int
    contracts: List[str]
    counterparties: Set[str]
    malicious_contracts: int
    verified_counterparties: int
    flagged_counterparties: int
    unverified_contracts: int
    active_days: int
    total_days: int

    @property
    def wallet_age_days(self) -> int:
        if self.first_tx_timestamp == 0:
            return 0
        return max(0, int((time.time() - self.first_tx_timestamp) / 86400))


class ChainFetcher:
    def __init__(self, base_rpc: str, eth_rpc: str):
        self.base_rpc = base_rpc
        self.eth_rpc = eth_rpc

    async def fetch_wallet(self, address: str) -> WalletData:
        base_data = await self._fetch_chain(address, self.base_rpc, "base")
        eth_data = await self._fetch_chain(address, self.eth_rpc, "ethereum")

        all_counterparties = base_data["counterparties"] | eth_data["counterparties"]
        all_contracts = base_data["contracts"] + eth_data["contracts"]
        first_tx = min(
            base_data["first_tx_timestamp"] or float("inf"),
            eth_data["first_tx_timestamp"] or float("inf"),
        )
        if first_tx == float("inf"):
            first_tx = 0

        return WalletData(
            tx_count=base_data["tx_count"] + eth_data["tx_count"],
            first_tx_timestamp=int(first_tx),
            contracts=all_contracts,
            counterparties=all_counterparties,
            malicious_contracts=0,
            verified_counterparties=0,
            flagged_counterparties=0,
            unverified_contracts=0,
            active_days=base_data.get("active_days", 0) + eth_data.get("active_days", 0),
            total_days=max(base_data.get("total_days", 0), eth_data.get("total_days", 0)),
        )

    async def _fetch_chain(self, address: str, rpc_url: str, chain: str) -> dict:
        """Fetch wallet data from a single chain via RPC + block explorer APIs."""
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        tx_count = w3.eth.get_transaction_count(Web3.to_checksum_address(address))

        return {
            "tx_count": tx_count,
            "first_tx_timestamp": 0,
            "contracts": [],
            "counterparties": set(),
            "active_days": 0,
            "total_days": 0,
        }
