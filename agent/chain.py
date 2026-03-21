import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Set, List
import httpx

logger = logging.getLogger(__name__)


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
    eth_balance: float = 0.0

    @property
    def wallet_age_days(self) -> int:
        if self.first_tx_timestamp == 0:
            return 0
        return max(0, int((time.time() - self.first_tx_timestamp) / 86400))


# Known malicious/flagged addresses on Base (common drainers, phishing)
KNOWN_FLAGGED = set()

# Known verified contracts (major protocols on Base)
KNOWN_VERIFIED = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC
    "0x4200000000000000000000000000000000000006",  # WETH
    "0x8004a169fb4a3325136eb29fa0ceb6d2e539a432",  # ERC-8004 Identity
    "0x8004baa17c55a88189ae136b182e5fda19de9b63",  # ERC-8004 Reputation
    "0x2626664c2603336e57b271c5c0b26f421741e481",  # Uniswap V3 Router
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # Uniswap Universal Router
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",  # USDbC
}


class ChainFetcher:
    def __init__(self, base_rpc: str, eth_rpc: str,
                 basescan_api_key: str = "", etherscan_api_key: str = ""):
        self.base_rpc = base_rpc
        self.eth_rpc = eth_rpc
        self.basescan_api_key = basescan_api_key
        self.etherscan_api_key = etherscan_api_key

    async def fetch_wallet(self, address: str) -> WalletData:
        base_data = await self._fetch_chain(address, self.base_rpc, "base")
        try:
            eth_data = await self._fetch_chain(address, self.eth_rpc, "ethereum")
        except Exception as e:
            logger.warning(f"ETH RPC failed for {address}, using Base-only data: {e}")
            eth_data = {
                "tx_count": 0, "first_tx_timestamp": 0,
                "contracts": [], "counterparties": set(),
                "active_days": 0, "total_days": 0,
            }

        # Fetch ETH balance on Base
        eth_balance = 0.0
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(self.base_rpc))
            bal_wei = await asyncio.to_thread(
                w3.eth.get_balance, Web3.to_checksum_address(address)
            )
            eth_balance = bal_wei / 1e18
        except Exception as e:
            logger.debug(f"Balance fetch failed for {address}: {e}")

        all_counterparties = base_data["counterparties"] | eth_data["counterparties"]
        all_contracts = base_data["contracts"] + eth_data["contracts"]
        first_tx = min(
            base_data["first_tx_timestamp"] or float("inf"),
            eth_data["first_tx_timestamp"] or float("inf"),
        )
        if first_tx == float("inf"):
            first_tx = 0

        # Classify counterparties and contracts
        verified = sum(1 for c in all_counterparties if c.lower() in KNOWN_VERIFIED)
        flagged = sum(1 for c in all_counterparties if c.lower() in KNOWN_FLAGGED)
        malicious = sum(1 for c in all_contracts if c.lower() in KNOWN_FLAGGED)
        unverified = len(all_contracts) - sum(1 for c in all_contracts if c.lower() in KNOWN_VERIFIED)

        return WalletData(
            tx_count=base_data["tx_count"] + eth_data["tx_count"],
            first_tx_timestamp=int(first_tx),
            contracts=all_contracts,
            counterparties=all_counterparties,
            malicious_contracts=max(0, malicious),
            verified_counterparties=verified,
            flagged_counterparties=flagged,
            unverified_contracts=max(0, unverified),
            active_days=base_data.get("active_days", 0) + eth_data.get("active_days", 0),
            total_days=max(base_data.get("total_days", 0), eth_data.get("total_days", 0)),
            eth_balance=eth_balance,
        )

    async def _fetch_chain(self, address: str, rpc_url: str, chain: str) -> dict:
        """Fetch wallet data from a single chain via block explorer API."""
        from web3 import Web3

        # Get tx count from RPC
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        tx_count = await asyncio.to_thread(
            w3.eth.get_transaction_count, Web3.to_checksum_address(address)
        )

        # Fetch transaction history from block explorer
        txs = await self._fetch_tx_history(address, chain)

        if not txs:
            return {
                "tx_count": tx_count,
                "first_tx_timestamp": 0,
                "contracts": [],
                "counterparties": set(),
                "active_days": 0,
                "total_days": 0,
            }

        # Parse transaction data
        first_ts = int(txs[-1].get("timeStamp", 0))  # oldest tx (API returns newest first)
        last_ts = int(txs[0].get("timeStamp", 0))

        counterparties = set()
        contracts = []
        active_dates = set()

        for tx in txs:
            ts = int(tx.get("timeStamp", 0))
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()

            # Track counterparties (addresses we interact with)
            if from_addr == address.lower() and to_addr:
                counterparties.add(to_addr)
            elif to_addr == address.lower() and from_addr:
                counterparties.add(from_addr)

            # Track contract interactions
            if tx.get("contractAddress"):
                contracts.append(tx["contractAddress"].lower())
            if to_addr and tx.get("input", "0x") != "0x":
                contracts.append(to_addr)

            # Track active days
            if ts > 0:
                day = ts // 86400
                active_dates.add(day)

        total_days = max(1, (last_ts - first_ts) // 86400) if first_ts > 0 else 0
        contracts = list(set(contracts))

        return {
            "tx_count": tx_count,
            "first_tx_timestamp": first_ts,
            "contracts": contracts,
            "counterparties": counterparties,
            "active_days": len(active_dates),
            "total_days": total_days,
        }

    async def _fetch_tx_history(self, address: str, chain: str) -> list:
        """Fetch transaction history from Blockscout API."""
        if chain == "base":
            base_url = "https://base.blockscout.com/api"
        else:
            base_url = "https://eth.blockscout.com/api"

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 100,
            "sort": "desc",
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(base_url, params=params)
                data = resp.json()
                if data.get("status") == "1" and data.get("result"):
                    return data["result"]
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch tx history for {address} on {chain}: {e}")
            return []
