# db.py
import aiosqlite
from datetime import datetime, timezone

class Database:
    def __init__(self, path: str = "sentinelnet.db"):
        self.path = path
        self.conn = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trust_scores (
                agent_id INTEGER PRIMARY KEY,
                wallet TEXT NOT NULL,
                trust_score INTEGER NOT NULL,
                longevity INTEGER NOT NULL,
                activity INTEGER NOT NULL,
                counterparty INTEGER NOT NULL,
                contract_risk INTEGER NOT NULL,
                agent_identity INTEGER NOT NULL DEFAULT 0,
                verdict TEXT NOT NULL,
                feedback_tx TEXT,
                evidence_uri TEXT,
                sybil_flagged BOOLEAN NOT NULL DEFAULT 0,
                scored_at TEXT NOT NULL
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                trust_score INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                longevity INTEGER NOT NULL,
                activity INTEGER NOT NULL,
                counterparty INTEGER NOT NULL,
                contract_risk INTEGER NOT NULL,
                agent_identity INTEGER NOT NULL DEFAULT 0,
                sybil_flagged BOOLEAN NOT NULL DEFAULT 0,
                scored_at TEXT NOT NULL
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                counterparty TEXT NOT NULL,
                interaction_count INTEGER DEFAULT 0,
                is_flagged BOOLEAN DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(agent_id, counterparty)
            )
        """)
        # Migration: add agent_identity + sybil_flagged columns if missing
        try:
            await self.conn.execute("ALTER TABLE trust_scores ADD COLUMN agent_identity INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            await self.conn.execute("ALTER TABLE trust_scores ADD COLUMN sybil_flagged BOOLEAN NOT NULL DEFAULT 0")
        except Exception:
            pass
        await self.conn.commit()

    async def save_score(self, agent_id, wallet, trust_score, longevity,
                         activity, counterparty, contract_risk, verdict,
                         feedback_tx, evidence_uri, agent_identity=0,
                         sybil_flagged=False):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT OR REPLACE INTO trust_scores
            (agent_id, wallet, trust_score, longevity, activity, counterparty,
             contract_risk, agent_identity, verdict, feedback_tx, evidence_uri,
             sybil_flagged, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, wallet, trust_score, longevity, activity, counterparty,
              contract_risk, agent_identity, verdict, feedback_tx, evidence_uri,
              int(sybil_flagged), now))
        # Record in history
        await self.conn.execute("""
            INSERT INTO score_history
            (agent_id, trust_score, verdict, longevity, activity, counterparty,
             contract_risk, agent_identity, sybil_flagged, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, trust_score, verdict, longevity, activity, counterparty,
              contract_risk, agent_identity, int(sybil_flagged), now))
        await self.conn.commit()

    async def get_score(self, agent_id):
        cursor = await self.conn.execute(
            "SELECT * FROM trust_scores WHERE agent_id = ?", (agent_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_scores(self):
        cursor = await self.conn.execute("SELECT * FROM trust_scores ORDER BY scored_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_score_history(self, agent_id, limit=50):
        cursor = await self.conn.execute(
            "SELECT * FROM score_history WHERE agent_id = ? ORDER BY scored_at DESC LIMIT ?",
            (agent_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def save_edge(self, agent_id, counterparty, interaction_count, is_flagged):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT INTO graph_edges (agent_id, counterparty, interaction_count, is_flagged, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, counterparty) DO UPDATE SET
                interaction_count = interaction_count + excluded.interaction_count,
                is_flagged = excluded.is_flagged,
                updated_at = excluded.updated_at
        """, (agent_id, counterparty, interaction_count, int(is_flagged), now))
        await self.conn.commit()

    async def get_edges(self, agent_id):
        cursor = await self.conn.execute(
            "SELECT * FROM graph_edges WHERE agent_id = ?", (agent_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_all_edges(self):
        cursor = await self.conn.execute("SELECT agent_id, counterparty FROM graph_edges")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def close(self):
        if self.conn:
            await self.conn.close()
