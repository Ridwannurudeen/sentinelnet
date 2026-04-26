"""Multi-RPC failover provider for web3.py.

Tries each RPC endpoint in order. On failure (network error, timeout, HTTP 5xx,
or rate-limit 429), advances to the next endpoint and remembers which one worked
last so subsequent calls go straight to the healthy one.
"""
from __future__ import annotations

import logging
import time
from typing import Any, List

import requests
from web3 import Web3
from web3.providers.rpc import HTTPProvider

log = logging.getLogger(__name__)

_TRANSIENT_HTTP = {429, 500, 502, 503, 504}


class FailoverHTTPProvider(HTTPProvider):
    """HTTPProvider that rotates through a list of RPC URLs on failure.

    Endpoints are tried in declared order. The index of the last endpoint that
    responded successfully is cached for `sticky_seconds`, so we don't punish a
    healthy primary every request after a one-off blip elsewhere.
    """

    def __init__(
        self,
        endpoints: List[str],
        request_kwargs: dict | None = None,
        sticky_seconds: int = 60,
    ):
        if not endpoints:
            raise ValueError("FailoverHTTPProvider requires at least one endpoint")
        self.endpoints = [e.strip() for e in endpoints if e.strip()]
        self._cur = 0
        self._cur_set_at = 0.0
        self._sticky = sticky_seconds
        super().__init__(self.endpoints[0], request_kwargs=request_kwargs)

    def _advance(self) -> None:
        self._cur = (self._cur + 1) % len(self.endpoints)
        self._cur_set_at = time.time()
        self.endpoint_uri = self.endpoints[self._cur]

    def _maybe_reset_to_primary(self) -> None:
        if self._cur != 0 and (time.time() - self._cur_set_at) > self._sticky:
            self._cur = 0
            self.endpoint_uri = self.endpoints[0]

    def make_request(self, method: str, params: Any) -> Any:
        self._maybe_reset_to_primary()
        last_err: Exception | None = None
        for _ in range(len(self.endpoints)):
            self.endpoint_uri = self.endpoints[self._cur]
            try:
                return super().make_request(method, params)
            except (
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                ConnectionError,
            ) as e:
                last_err = e
                log.warning("RPC %s failed (%s) — failing over", self.endpoint_uri, e.__class__.__name__)
                self._advance()
                continue
            except Exception as e:
                msg = str(e).lower()
                code: int | None = None
                resp = getattr(e, "response", None)
                if resp is not None and hasattr(resp, "status_code"):
                    code = resp.status_code
                if code in _TRANSIENT_HTTP or any(s in msg for s in ("rate limit", "too many requests", "timeout", "503", "502", "504", "429")):
                    last_err = e
                    log.warning("RPC %s transient error (%s) — failing over", self.endpoint_uri, e.__class__.__name__)
                    self._advance()
                    continue
                raise
        raise RuntimeError(f"All RPC endpoints failed; last error: {last_err}")


def make_web3(urls_csv: str, fallback_single: str = "") -> Web3:
    """Build a Web3 instance with multi-RPC failover.

    `urls_csv` is a comma-separated list (from `BASE_RPC_URLS`). If empty, falls
    back to the single `fallback_single` URL.
    """
    raw = (urls_csv or fallback_single or "").strip()
    if not raw:
        raise ValueError("No RPC URL configured")
    urls = [u.strip() for u in raw.split(",") if u.strip()]
    return Web3(FailoverHTTPProvider(urls, request_kwargs={"timeout": 10}))
