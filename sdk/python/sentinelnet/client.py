"""SentinelNet Python client for trust scoring ERC-8004 agents."""

import httpx
from typing import Optional, List, Dict, Any

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

    def _get(self, path: str, **params) -> dict:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict) -> dict:
        r = self._client.post(path, json=json)
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        """Check API health."""
        return self._get("/api/health")

    def get_trust(self, agent_id: int) -> dict:
        """Get trust score for an agent.

        Returns dict with trust_score, verdict, explanation, dimension scores.
        Raises httpx.HTTPStatusError if agent not scored (404).
        """
        return self._get(f"/trust/{agent_id}")

    def get_scores(self, apply_decay: bool = True) -> dict:
        """Get all scored agents with verdict breakdown."""
        return self._get("/api/scores", apply_decay=str(apply_decay).lower())

    def get_stats(self) -> dict:
        """Aggregate trust statistics across all scored agents."""
        return self._get("/api/stats")

    def get_history(self, agent_id: int, limit: int = 50) -> dict:
        """Get scoring history for an agent."""
        return self._get(f"/trust/{agent_id}/history", limit=limit)

    def get_graph(self, agent_id: int) -> dict:
        """Get an agent's counterparty trust neighborhood."""
        return self._get(f"/trust/graph/{agent_id}")

    def batch_trust(self, agent_ids: List[int]) -> dict:
        """Query trust scores for multiple agents at once (max 100)."""
        return self._post("/trust/batch", json={"agent_ids": agent_ids})

    def get_threats(self, limit: int = 50) -> dict:
        """Get real-time threat intelligence feed."""
        return self._get("/api/threats", limit=limit)

    def get_graph_data(self) -> dict:
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

    def get_comparison(self, agent_ids: List[int]) -> dict:
        """Compare trust scores side-by-side for multiple agents."""
        ids_str = ",".join(str(i) for i in agent_ids)
        return self._get("/trust/compare", agents=ids_str)

    def get_anomalies(self) -> dict:
        """Get statistical anomalies detected across the agent ecosystem."""
        return self._get("/api/anomalies")

    def get_classification(self, agent_id: int) -> dict:
        """Get behavioral classification for an agent."""
        return self._get(f"/api/classify/{agent_id}")

    def register_webhook(self, url: str, events: List[str], secret: str = None) -> dict:
        """Register a webhook for real-time notifications."""
        payload = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret
        return self._post("/api/webhooks", json=payload)

    def list_webhooks(self) -> dict:
        """List all registered webhooks."""
        return self._get("/api/webhooks")

    def delete_webhook(self, webhook_id: str) -> dict:
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

    async def _get(self, path: str, **params) -> dict:
        r = await self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, json: dict) -> dict:
        r = await self._client.post(path, json=json)
        r.raise_for_status()
        return r.json()

    async def health(self) -> dict:
        return await self._get("/api/health")

    async def get_trust(self, agent_id: int) -> dict:
        return await self._get(f"/trust/{agent_id}")

    async def get_scores(self, apply_decay: bool = True) -> dict:
        return await self._get("/api/scores", apply_decay=str(apply_decay).lower())

    async def get_stats(self) -> dict:
        return await self._get("/api/stats")

    async def get_history(self, agent_id: int, limit: int = 50) -> dict:
        return await self._get(f"/trust/{agent_id}/history", limit=limit)

    async def get_graph(self, agent_id: int) -> dict:
        return await self._get(f"/trust/graph/{agent_id}")

    async def batch_trust(self, agent_ids: List[int]) -> dict:
        return await self._post("/trust/batch", json={"agent_ids": agent_ids})

    async def get_threats(self, limit: int = 50) -> dict:
        return await self._get("/api/threats", limit=limit)

    async def get_graph_data(self) -> dict:
        return await self._get("/api/graph-data")

    def badge_url(self, agent_id: int) -> str:
        return f"{self.base_url}/badge/{agent_id}.svg"

    async def is_trusted(self, agent_id: int) -> bool:
        try:
            score = await self.get_trust(agent_id)
            return score.get("verdict") == "TRUST"
        except httpx.HTTPStatusError:
            return False

    async def trust_gate(self, agent_id: int, min_score: int = 55) -> bool:
        try:
            score = await self.get_trust(agent_id)
            return score.get("trust_score", 0) >= min_score and not score.get("sybil_flagged")
        except httpx.HTTPStatusError:
            return False

    async def get_comparison(self, agent_ids: List[int]) -> dict:
        """Compare trust scores side-by-side for multiple agents."""
        ids_str = ",".join(str(i) for i in agent_ids)
        return await self._get("/trust/compare", agents=ids_str)

    async def get_anomalies(self) -> dict:
        """Get statistical anomalies detected across the agent ecosystem."""
        return await self._get("/api/anomalies")

    async def get_classification(self, agent_id: int) -> dict:
        """Get behavioral classification for an agent."""
        return await self._get(f"/api/classify/{agent_id}")

    async def register_webhook(self, url: str, events: List[str], secret: str = None) -> dict:
        """Register a webhook for real-time notifications."""
        payload = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret
        return await self._post("/api/webhooks", json=payload)

    async def list_webhooks(self) -> dict:
        """List all registered webhooks."""
        return await self._get("/api/webhooks")

    async def delete_webhook(self, webhook_id: str) -> dict:
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
