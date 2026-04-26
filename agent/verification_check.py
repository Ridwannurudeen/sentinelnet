"""BaseScan source-code verification check with on-disk cache.

Used by the contract-risk dimension to credit agents whose interacted contracts
are source-verified on BaseScan (a positive trust signal beyond the small
hand-curated KNOWN_VERIFIED list).
"""
from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Iterable

import httpx

log = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "verification_cache.db"
_CACHE_TTL_SECONDS = 7 * 24 * 3600
_BASESCAN_URL = "https://api.basescan.org/api"


def _conn() -> sqlite3.Connection:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_CACHE_PATH, isolation_level=None, timeout=5)
    c.execute(
        "CREATE TABLE IF NOT EXISTS verification ("
        "address TEXT PRIMARY KEY, verified INTEGER, checked_at INTEGER)"
    )
    return c


def _read_cache(addresses: Iterable[str]) -> dict[str, bool]:
    addrs = [a.lower() for a in addresses]
    if not addrs:
        return {}
    fresh_cutoff = int(time.time()) - _CACHE_TTL_SECONDS
    placeholders = ",".join("?" for _ in addrs)
    with _conn() as c:
        rows = c.execute(
            f"SELECT address, verified FROM verification "
            f"WHERE address IN ({placeholders}) AND checked_at > ?",
            (*addrs, fresh_cutoff),
        ).fetchall()
    return {addr: bool(v) for addr, v in rows}


def _write_cache(results: dict[str, bool]) -> None:
    if not results:
        return
    now = int(time.time())
    with _conn() as c:
        c.executemany(
            "INSERT OR REPLACE INTO verification(address, verified, checked_at) VALUES(?,?,?)",
            [(a.lower(), int(v), now) for a, v in results.items()],
        )


async def _check_one(client: httpx.AsyncClient, address: str, api_key: str) -> bool:
    try:
        r = await client.get(
            _BASESCAN_URL,
            params={
                "module": "contract",
                "action": "getsourcecode",
                "address": address,
                "apikey": api_key,
            },
        )
        if r.status_code != 200:
            return False
        data = r.json()
        if data.get("status") != "1":
            return False
        result = data.get("result") or []
        if not result:
            return False
        src = (result[0].get("SourceCode") or "").strip()
        return bool(src)
    except Exception as e:
        log.debug("verification check failed for %s: %s", address, e)
        return False


async def filter_verified(addresses: Iterable[str], api_key: str) -> set[str]:
    """Return the subset of addresses confirmed source-verified on BaseScan.

    Uses a 7-day on-disk cache. Without an `api_key`, returns whatever is in
    cache and skips network checks.
    """
    addrs = sorted({a.lower() for a in addresses if a})
    if not addrs:
        return set()

    cached = _read_cache(addrs)
    verified = {a for a, v in cached.items() if v}
    to_check = [a for a in addrs if a not in cached]

    if not to_check or not api_key:
        return verified

    fresh: dict[str, bool] = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for a in to_check:
            ok = await _check_one(client, a, api_key)
            fresh[a] = ok
            if ok:
                verified.add(a)
    _write_cache(fresh)
    return verified
