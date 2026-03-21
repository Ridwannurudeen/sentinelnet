import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Progressive scan: score this many new agents per sweep
BATCH_SIZE = 100
# Also rescore stale agents each sweep (cap)
STALE_CAP = 50


class Discovery:
    def __init__(self, erc8004, db, pipeline, self_agent_id: int,
                 sweep_interval: int = 1800, rescore_after_hours: int = 24,
                 on_sweep_complete=None):
        self.erc8004 = erc8004
        self.db = db
        self.pipeline = pipeline
        self.self_agent_id = self_agent_id
        self.sweep_interval = sweep_interval
        self.rescore_after_hours = rescore_after_hours
        self.on_sweep_complete = on_sweep_complete
        self._running = False
        # Cursor tracks where the progressive scan left off
        self._scan_cursor = 1
        self._total_agents = 0

    async def find_new_agents(self) -> list:
        self._total_agents = await self.erc8004.get_total_agents()
        scored = await self.db.get_all_scores()
        scored_ids = {s["agent_id"] for s in scored}

        # Progressive full-registry scan: pick up from cursor, wrap around
        candidates = []
        start = self._scan_cursor
        end = min(start + BATCH_SIZE * 3, self._total_agents + 1)  # scan 3x batch to find enough unscored

        for i in range(start, end):
            if i not in scored_ids and i != self.self_agent_id:
                candidates.append(i)
            if len(candidates) >= BATCH_SIZE:
                break

        # Advance cursor past what we scanned
        self._scan_cursor = end if end <= self._total_agents else 1

        # If we wrapped or ran low, also grab recent high-ID agents (new registrations)
        if len(candidates) < BATCH_SIZE:
            high_start = max(1, self._total_agents - 200)
            for i in range(high_start, self._total_agents + 1):
                if i not in scored_ids and i != self.self_agent_id and i not in candidates:
                    candidates.append(i)
                if len(candidates) >= BATCH_SIZE:
                    break

        coverage = len(scored_ids)
        logger.info(
            f"Registry scan: {coverage}/{self._total_agents} agents scored "
            f"({coverage * 100 // max(self._total_agents, 1)}% coverage), "
            f"cursor at {self._scan_cursor}, {len(candidates)} new targets"
        )
        return candidates

    async def find_stale_agents(self) -> list:
        scores = await self.db.get_all_scores()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.rescore_after_hours)
        stale = []
        for s in scores:
            scored_at = datetime.fromisoformat(s["scored_at"])
            if scored_at < cutoff:
                stale.append(s["agent_id"])
        return stale[:STALE_CAP]

    async def sweep(self):
        logger.info("Discovery sweep started")
        new_agents = await self.find_new_agents()
        stale_agents = await self.find_stale_agents()
        # New agents first, then stale rescores
        targets = list(dict.fromkeys(new_agents + stale_agents))
        cap = BATCH_SIZE + STALE_CAP
        if len(targets) > cap:
            targets = targets[:cap]
        logger.info(
            f"Sweep: {len(new_agents)} new, {len(stale_agents)} stale, "
            f"{len(targets)} total targets"
        )
        scored = 0
        for agent_id in targets:
            try:
                await self.pipeline(agent_id)
                scored += 1
            except Exception as e:
                logger.error(f"Failed to score agent {agent_id}: {e}")
            await asyncio.sleep(1.5)  # Rate limit
        # Run post-sweep analysis (sybil detection, contagion)
        if self.on_sweep_complete:
            try:
                await self.on_sweep_complete()
            except Exception as e:
                logger.error(f"Post-sweep analysis failed: {e}")
        logger.info(f"Discovery sweep complete: scored {scored}/{len(targets)} agents")

    async def run_loop(self):
        self._running = True
        while self._running:
            await self.sweep()
            await asyncio.sleep(self.sweep_interval)

    def stop(self):
        self._running = False
