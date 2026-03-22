"""SentinelNet Python client for trust scoring ERC-8004 agents."""

from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional

DEFAULT_BASE_URL = "https://sentinelnet.gudman.xyz"


class SentinelNet:
    """Synchronous SentinelNet client.

    Usage:
        from sentinelnet import SentinelNet

        sn = SentinelNet()
        score = sn.get_trust(31253)
        print(score["verdict"])  # TRUST | CAUTION | REJECT
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _get(self, path: str, **params: Any) -> Dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        r = self._client.post(path, json=json)
        r.raise_for_status()
        return r.json()

    def health(self) -> Dict[str, Any]:
        """Check API health."""
        return self._get("/api/health")

    def get_trust(self, agent_id: int) -> Dict[str, Any]:
        """Get trust score for an agent.

        Returns dict with trust_score, verdict, explanation, dimension scores.
        Raises httpx.HTTPStatusError if agent not scored (404).
        """
        return self._get(f"/trust/{agent_id}")

    def get_scores(self, apply_decay: bool = True) -> Dict[str, Any]:
        """Get all scored agents with verdict breakdown."""
        return self._get("/api/scores", apply_decay=str(apply_decay).lower())

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate trust statistics across all scored agents."""
        return self._get("/api/stats")

    def get_history(self, agent_id: int, limit: int = 50) -> Dict[str, Any]:
        """Get scoring history for an agent."""
        return self._get(f"/trust/{agent_id}/history", limit=limit)

    def get_graph(self, agent_id: int) -> Dict[str, Any]:
        """Get an agent's counterparty trust neighborhood."""
        return self._get(f"/trust/graph/{agent_id}")

    def batch_trust(self, agent_ids: List[int]) -> Dict[str, Any]:
        """Query trust scores for multiple agents at once (max 100)."""
        return self._post("/trust/batch", json={"agent_ids": agent_ids})

    def get_threats(self, limit: int = 50) -> Dict[str, Any]:
        """Get real-time threat intelligence feed."""
        return self._get("/api/threats", limit=limit)

    def get_graph_data(self) -> Dict[str, Any]:
        """Get full agent interaction graph (nodes + links)."""
        return self._get("/api/graph-data")

    def badge_url(self, agent_id: int) -> str:
        """Get embeddable SVG badge URL for an agent."""
        return f"{self.base_url}/badge/{agent_id}.svg"

    def is_trusted(self, agent_id: int) -> bool:
        """Quick check: is this agent trusted?"""
        try:
            score = self.get_trust(agent_id)
            return score.get("verdict") == "TRUST"
        except httpx.HTTPStatusError:
            return False

    def trust_gate(self, agent_id: int, min_score: int = 55) -> bool:
        """Gate an interaction: only proceed if agent meets minimum trust score."""
        try:
            score = self.get_trust(agent_id)
            return score.get("trust_score", 0) >= min_score and not score.get("sybil_flagged")
        except httpx.HTTPStatusError:
            return False

    def get_comparison(self, agent_ids: List[int]) -> Dict[str, Any]:
        """Compare trust scores side-by-side for multiple agents."""
        ids_str = ",".join(str(i) for i in agent_ids)
        return self._get("/trust/compare", agents=ids_str)

    def get_anomalies(self) -> Dict[str, Any]:
        """Get statistical anomalies detected across the agent ecosystem."""
        return self._get("/api/anomalies")

    def get_classification(self, agent_id: int) -> Dict[str, Any]:
        """Get behavioral classification for an agent."""
        return self._get(f"/api/classify/{agent_id}")

    def register_webhook(self, url: str, events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """Register a webhook for real-time notifications."""
        payload: Dict[str, Any] = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret
        return self._post("/api/webhooks", json=payload)

    def list_webhooks(self) -> Dict[str, Any]:
        """List all registered webhooks."""
        return self._get("/api/webhooks")

    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook by ID."""
        webhook_id = str(webhook_id).replace("/", "").replace("..", "")
        r = self._client.delete(f"/api/webhooks/{webhook_id}")
        r.raise_for_status()
        return r.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncSentinelNet:
    """Async SentinelNet client.

    Usage:
        from sentinelnet import AsyncSentinelNet

        async with AsyncSentinelNet() as sn:
            score = await sn.get_trust(31253)
            print(score["verdict"])
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def _get(self, path: str, **params: Any) -> Dict[str, Any]:
        r = await self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        r = await self._client.post(path, json=json)
        r.raise_for_status()
        return r.json()

    async def health(self) -> Dict[str, Any]:
        """Check API health."""
        return await self._get("/api/health")

    async def get_trust(self, agent_id: int) -> Dict[str, Any]:
        """Get trust score for an agent.

        Returns dict with trust_score, verdict, explanation, dimension scores.
        Raises httpx.HTTPStatusError if agent not scored (404).
        """
        return await self._get(f"/trust/{agent_id}")

    async def get_scores(self, apply_decay: bool = True) -> Dict[str, Any]:
        """Get all scored agents with verdict breakdown."""
        return await self._get("/api/scores", apply_decay=str(apply_decay).lower())

    async def get_stats(self) -> Dict[str, Any]:
        """Aggregate trust statistics across all scored agents."""
        return await self._get("/api/stats")

    async def get_history(self, agent_id: int, limit: int = 50) -> Dict[str, Any]:
        """Get scoring history for an agent."""
        return await self._get(f"/trust/{agent_id}/history", limit=limit)

    async def get_graph(self, agent_id: int) -> Dict[str, Any]:
        """Get an agent's counterparty trust neighborhood."""
        return await self._get(f"/trust/graph/{agent_id}")

    async def batch_trust(self, agent_ids: List[int]) -> Dict[str, Any]:
        """Query trust scores for multiple agents at once (max 100)."""
        return await self._post("/trust/batch", json={"agent_ids": agent_ids})

    async def get_threats(self, limit: int = 50) -> Dict[str, Any]:
        """Get real-time threat intelligence feed."""
        return await self._get("/api/threats", limit=limit)

    async def get_graph_data(self) -> Dict[str, Any]:
        """Get full agent interaction graph (nodes + links)."""
        return await self._get("/api/graph-data")

    def badge_url(self, agent_id: int) -> str:
        """Get embeddable SVG badge URL for an agent."""
        return f"{self.base_url}/badge/{agent_id}.svg"

    async def is_trusted(self, agent_id: int) -> bool:
        """Quick check: is this agent trusted?"""
        try:
            score = await self.get_trust(agent_id)
            return score.get("verdict") == "TRUST"
        except httpx.HTTPStatusError:
            return False

    async def trust_gate(self, agent_id: int, min_score: int = 55) -> bool:
        """Gate an interaction: only proceed if agent meets minimum trust score."""
        try:
            score = await self.get_trust(agent_id)
            return score.get("trust_score", 0) >= min_score and not score.get("sybil_flagged")
        except httpx.HTTPStatusError:
            return False

    async def get_comparison(self, agent_ids: List[int]) -> Dict[str, Any]:
        """Compare trust scores side-by-side for multiple agents."""
        ids_str = ",".join(str(i) for i in agent_ids)
        return await self._get("/trust/compare", agents=ids_str)

    async def get_anomalies(self) -> Dict[str, Any]:
        """Get statistical anomalies detected across the agent ecosystem."""
        return await self._get("/api/anomalies")

    async def get_classification(self, agent_id: int) -> Dict[str, Any]:
        """Get behavioral classification for an agent."""
        return await self._get(f"/api/classify/{agent_id}")

    async def register_webhook(self, url: str, events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """Register a webhook for real-time notifications."""
        payload: Dict[str, Any] = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret
        return await self._post("/api/webhooks", json=payload)

    async def list_webhooks(self) -> Dict[str, Any]:
        """List all registered webhooks."""
        return await self._get("/api/webhooks")

    async def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook by ID."""
        webhook_id = str(webhook_id).replace("/", "").replace("..", "")
        r = await self._client.delete(f"/api/webhooks/{webhook_id}")
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
