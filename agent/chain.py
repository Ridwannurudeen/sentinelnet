import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Set, List, Optional
import httpx

logger = logging.getLogger(__name__)


class RPCPool:
    """Round-robin RPC pool with automatic failover on errors."""

    def __init__(self, urls: List[str], chain_name: str = "unknown"):
        if not urls:
            raise ValueError(f"RPCPool for {chain_name}: at least one URL required")
        self.urls = urls
        self.chain_name = chain_name
        self._active_idx = 0
        self._max_retries = len(urls)

    @property
    def active_url(self) -> str:
        return self.urls[self._active_idx]

    def _rotate(self):
        old = self.urls[self._active_idx]
        self._active_idx = (self._active_idx + 1) % len(self.urls)
        logger.warning(
            f"RPCPool[{self.chain_name}]: rotating from {old} -> {self.urls[self._active_idx]}"
        )

    def get_web3(self):
        """Return a Web3 instance for the currently active URL."""
        from web3 import Web3
        return Web3(Web3.HTTPProvider(self.active_url))

    async def call(self, fn, *args, **kwargs):
        """Execute an async-wrapped RPC call with retry + failover.

        `fn` receives a Web3 instance and should return a result.
        Example: await pool.call(lambda w3: w3.eth.get_balance(addr))
        """
        last_err = None
        for attempt in range(self._max_retries):
            w3 = self.get_web3()
            try:
                result = await asyncio.to_thread(fn, w3)
                return result
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                is_rpc_error = any(t in err_str for t in [
                    "429", "too many requests", "timeout", "timed out",
                    "connection", "502", "503", "504", "rate limit",
                ])
                if is_rpc_error and attempt < self._max_retries - 1:
                    self._rotate()
                    await asyncio.sleep(1)
                else:
                    raise
        raise last_err


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
    tx_timestamps: List[int] = field(default_factory=list)
    funding_source: str = "unknown"  # "cex", "faucet", "contract", "eoa", "unknown"

    @property
    def wallet_age_days(self) -> int:
        if self.first_tx_timestamp == 0:
            return 0
        return max(0, int((time.time() - self.first_tx_timestamp) / 86400))


# Known CEX hot wallets on Base (KYC'd funding sources)
KNOWN_CEX = {
    "0x3304e22ddaa22bcdc5fca2269b418046ae7b566a",  # Coinbase
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",  # Coinbase 2
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 2
    "0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23",  # Bybit
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",  # FTX (pre-collapse)
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance 14
}

# Known faucet addresses on Base
KNOWN_FAUCET = {
    "0x0000000000000000000000000000000000000000",  # null address (genesis)
}

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
                 basescan_api_key: str = "", etherscan_api_key: str = "",
                 base_rpc_urls: Optional[List[str]] = None,
                 eth_rpc_urls: Optional[List[str]] = None):
        self.base_rpc = base_rpc
        self.eth_rpc = eth_rpc
        self.basescan_api_key = basescan_api_key
        self.etherscan_api_key = etherscan_api_key

        # Multi-RPC pools (fall back to single URL if no list provided)
        self.base_pool = RPCPool(
            base_rpc_urls if base_rpc_urls else [base_rpc], chain_name="base"
        )
        self.eth_pool = RPCPool(
            eth_rpc_urls if eth_rpc_urls else [eth_rpc], chain_name="ethereum"
        )

    async def fetch_wallet(self, address: str) -> WalletData:
        base_data = await self._fetch_chain(address, self.base_pool, "base")
        try:
            eth_data = await self._fetch_chain(address, self.eth_pool, "ethereum")
        except Exception as e:
            logger.warning(f"ETH RPC failed for {address}, using Base-only data: {e}")
            eth_data = {
                "tx_count": 0, "first_tx_timestamp": 0,
                "contracts": [], "counterparties": set(),
                "active_days": 0, "total_days": 0,
                "tx_timestamps": [], "funding_source": "unknown",
            }

        # Fetch ETH balance on Base (via pool with failover)
        eth_balance = 0.0
        try:
            from web3 import Web3
            checksum = Web3.to_checksum_address(address)
            bal_wei = await self.base_pool.call(
                lambda w3: w3.eth.get_balance(checksum)
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

        # Merge tx timestamps from both chains
        all_timestamps = base_data.get("tx_timestamps", []) + eth_data.get("tx_timestamps", [])
        all_timestamps.sort()

        # Use Base funding source (primary chain) — fall back to ETH if unknown
        funding_source = base_data.get("funding_source", "unknown")
        if funding_source == "unknown":
            funding_source = eth_data.get("funding_source", "unknown")

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
            tx_timestamps=all_timestamps,
            funding_source=funding_source,
        )

    async def _fetch_chain(self, address: str, pool: RPCPool, chain: str) -> dict:
        """Fetch wallet data from a single chain via block explorer API."""
        from web3 import Web3

        # Get tx count from RPC (with failover)
        checksum = Web3.to_checksum_address(address)
        tx_count = await pool.call(
            lambda w3: w3.eth.get_transaction_count(checksum)
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
        tx_timestamps = []
        first_incoming_from = None

        for tx in txs:
            ts = int(tx.get("timeStamp", 0))
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()

            if ts > 0:
                tx_timestamps.append(ts)

            # Track counterparties (addresses we interact with)
            if from_addr == address.lower() and to_addr:
                counterparties.add(to_addr)
            elif to_addr == address.lower() and from_addr:
                counterparties.add(from_addr)
                # Track first incoming tx source (oldest = last in desc-sorted list)
                first_incoming_from = from_addr

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

        # Classify funding source from first incoming tx
        funding_source = "unknown"
        if first_incoming_from:
            if first_incoming_from in KNOWN_CEX:
                funding_source = "cex"
            elif first_incoming_from in KNOWN_FAUCET:
                funding_source = "faucet"
            else:
                funding_source = "eoa"

        return {
            "tx_count": tx_count,
            "first_tx_timestamp": first_ts,
            "contracts": contracts,
            "counterparties": counterparties,
            "active_days": len(active_dates),
            "total_days": total_days,
            "tx_timestamps": tx_timestamps,
            "funding_source": funding_source,
        }

    async def _fetch_tx_history(self, address: str, chain: str) -> list:
        """Fetch transaction history from Blockscout API (paginated, up to 1000 txns)."""
        if chain == "base":
            base_url = "https://base.blockscout.com/api"
        else:
            base_url = "https://eth.blockscout.com/api"

        PAGE_SIZE = 100
        MAX_PAGES = 10  # 1000 txns max
        all_txs = []

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                for page in range(1, MAX_PAGES + 1):
                    params = {
                        "module": "account",
                        "action": "txlist",
                        "address": address,
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": page,
                        "offset": PAGE_SIZE,
                        "sort": "desc",
                    }
                    resp = await client.get(base_url, params=params)
                    data = resp.json()
                    if data.get("status") != "1" or not data.get("result"):
                        break
                    batch = data["result"]
                    all_txs.extend(batch)
                    if len(batch) < PAGE_SIZE:
                        break  # last page
        except Exception as e:
            logger.warning(f"Failed to fetch tx history for {address} on {chain}: {e}")

        return all_txs
