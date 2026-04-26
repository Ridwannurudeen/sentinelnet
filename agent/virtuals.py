"""Virtual Protocol agent discovery and wallet mapping.

Pulls agents from the public Virtuals API, extracts the sentient wallet
(the AI's autonomous operating wallet), and feeds it into the existing
SentinelNet scoring pipeline.

API: https://api.virtuals.io/api/virtuals?filters[chain]=BASE&pagination[page]=N&pagination[pageSize]=M
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger(__name__)

API_URL = "https://api.virtuals.io/api/virtuals"
DEFAULT_TIMEOUT = 15


@dataclass
class VirtualAgent:
    virtual_id: int
    name: str
    symbol: str
    sentient_wallet: str
    creator_wallet: str
    token_address: Optional[str]
    tba_address: Optional[str]
    mcap_in_virtual: float
    holder_count: int
    chain: str

    @property
    def primary_wallet(self) -> str:
        """Wallet to score: prefer sentient (AI's autonomous wallet), fall back to creator."""
        return self.sentient_wallet or self.creator_wallet


class VirtualsClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    async def fetch_one(self, virtual_id: int) -> Optional[VirtualAgent]:
        """Fetch a single Virtual agent by ID."""
        params = {
            "filters[id]": virtual_id,
            "filters[chain]": "BASE",
            "pagination[page]": 1,
            "pagination[pageSize]": 1,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json().get("data", [])
        if not data:
            return None
        return _parse(data[0])

    async def fetch_page(self, page: int = 1, page_size: int = 50) -> tuple[list[VirtualAgent], int]:
        """Fetch a page of Base-chain Virtuals. Returns (agents, total_count)."""
        params = {
            "filters[chain]": "BASE",
            "pagination[page]": page,
            "pagination[pageSize]": min(page_size, 100),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(API_URL, params=params)
            r.raise_for_status()
            payload = r.json()
        agents = [_parse(d) for d in payload.get("data", []) if _parse(d)]
        agents = [a for a in agents if a is not None]
        total = payload.get("meta", {}).get("pagination", {}).get("total", 0)
        return agents, total

    async def fetch_top_by_mcap(self, limit: int = 100) -> list[VirtualAgent]:
        """Fetch the top-N Virtuals by market cap on Base."""
        params = {
            "filters[chain]": "BASE",
            "sort[0]": "mcapInVirtual:desc",
            "pagination[page]": 1,
            "pagination[pageSize]": min(limit, 100),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json().get("data", [])
        out = [_parse(d) for d in data]
        return [a for a in out if a is not None]


def _parse(d: dict) -> Optional[VirtualAgent]:
    """Convert a raw Virtuals API record into a VirtualAgent."""
    sentient = (d.get("sentientWalletAddress") or "").strip()
    creator = (d.get("walletAddress") or "").strip()
    if not sentient and not creator:
        return None
    try:
        return VirtualAgent(
            virtual_id=int(d["id"]),
            name=d.get("name") or "",
            symbol=d.get("symbol") or "",
            sentient_wallet=sentient,
            creator_wallet=creator,
            token_address=d.get("tokenAddress"),
            tba_address=d.get("tbaAddress"),
            mcap_in_virtual=float(d.get("mcapInVirtual") or 0),
            holder_count=int(d.get("holderCount") or 0),
            chain=d.get("chain") or "BASE",
        )
    except (KeyError, ValueError, TypeError) as e:
        log.warning("Failed to parse Virtual record: %s", e)
        return None
