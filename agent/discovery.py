import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class Discovery:
    def __init__(self, erc8004, db, pipeline, self_agent_id: int,
                 sweep_interval: int = 1800, rescore_after_hours: int = 24):
        self.erc8004 = erc8004
        self.db = db
        self.pipeline = pipeline
        self.self_agent_id = self_agent_id
        self.sweep_interval = sweep_interval
        self.rescore_after_hours = rescore_after_hours
        self._running = False

    async def find_new_agents(self) -> list:
        total = await self.erc8004.get_total_agents()
        scored = await self.db.get_all_scores()
        scored_ids = {s["agent_id"] for s in scored}

        # Mix early agents (1-100) with recent high-ID agents (Synthesis participants)
        # This gives score diversity: old established wallets vs new hackathon wallets
        early_ids = [
            i for i in range(1, min(101, total + 1))
            if i not in scored_ids and i != self.self_agent_id
        ]
        # Sample high-ID agents (recent registrations, likely hackathon participants)
        high_start = max(1, total - 200)
        high_ids = [
            i for i in range(high_start, total + 1)
            if i not in scored_ids and i != self.self_agent_id
        ]
        # Combine, deduplicate, interleave for variety
        combined = list(dict.fromkeys(high_ids + early_ids))
        return combined

    async def find_stale_agents(self) -> list:
        scores = await self.db.get_all_scores()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.rescore_after_hours)
        stale = []
        for s in scores:
            scored_at = datetime.fromisoformat(s["scored_at"])
            if scored_at < cutoff:
                stale.append(s["agent_id"])
        return stale

    async def sweep(self):
        logger.info("Discovery sweep started")
        new_agents = await self.find_new_agents()
        stale_agents = await self.find_stale_agents()
        targets = list(set(new_agents + stale_agents))
        # Cap per sweep to avoid overwhelming RPCs
        if len(targets) > 50:
            targets = targets[:50]
            logger.info(f"Sweep: {len(new_agents)} new, {len(stale_agents)} stale, capped to {len(targets)} targets")
        else:
            logger.info(f"Sweep: {len(new_agents)} new, {len(stale_agents)} stale, {len(targets)} total targets")
        for agent_id in targets:
            try:
                await self.pipeline(agent_id)
            except Exception as e:
                logger.error(f"Failed to score agent {agent_id}: {e}")
            await asyncio.sleep(2)  # Rate limit: avoid hammering RPCs/APIs
        logger.info("Discovery sweep complete")

    async def run_loop(self):
        self._running = True
        while self._running:
            await self.sweep()
            await asyncio.sleep(self.sweep_interval)

    def stop(self):
        self._running = False
