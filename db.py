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
                contagion_adjustment INTEGER NOT NULL DEFAULT 0,
                attestation_uid TEXT DEFAULT '',
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
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS threats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                threat_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                agent_id INTEGER,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Migrations for existing DBs
        for col, typedef in [
            ("agent_identity", "INTEGER NOT NULL DEFAULT 0"),
            ("sybil_flagged", "BOOLEAN NOT NULL DEFAULT 0"),
            ("contagion_adjustment", "INTEGER NOT NULL DEFAULT 0"),
            ("attestation_uid", "TEXT DEFAULT ''"),
        ]:
            try:
                await self.conn.execute(f"ALTER TABLE trust_scores ADD COLUMN {col} {typedef}")
            except Exception:
                pass
        await self.conn.commit()

    async def save_score(self, agent_id, wallet, trust_score, longevity,
                         activity, counterparty, contract_risk, verdict,
                         feedback_tx, evidence_uri, agent_identity=0,
                         sybil_flagged=False, contagion_adjustment=0,
                         attestation_uid=""):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT OR REPLACE INTO trust_scores
            (agent_id, wallet, trust_score, longevity, activity, counterparty,
             contract_risk, agent_identity, verdict, feedback_tx, evidence_uri,
             sybil_flagged, contagion_adjustment, attestation_uid, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, wallet, trust_score, longevity, activity, counterparty,
              contract_risk, agent_identity, verdict, feedback_tx, evidence_uri,
              int(sybil_flagged), contagion_adjustment, attestation_uid, now))
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
        cursor = await self.conn.execute(
            "SELECT agent_id, counterparty, interaction_count FROM graph_edges"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ─── Threats ───

    async def save_threat(self, threat_type, severity, agent_id, details):
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute("""
            INSERT INTO threats (threat_type, severity, agent_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (threat_type, severity, agent_id, details, now))
        await self.conn.commit()

    async def get_threats(self, limit=50):
        cursor = await self.conn.execute(
            "SELECT * FROM threats ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_wallet_agent_map(self):
        """Get wallet → [agent_ids] mapping for sybil detection."""
        cursor = await self.conn.execute(
            "SELECT agent_id, wallet FROM trust_scores"
        )
        rows = await cursor.fetchall()
        wallet_agents = {}
        for r in rows:
            w = r["wallet"].lower()
            wallet_agents.setdefault(w, []).append(r["agent_id"])
        return wallet_agents

    # ─── Webhooks ───

    async def save_webhook(self, wh_id, url, events):
        """Persist a webhook registration."""
        import json
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT INTO webhooks (id, url, events, created_at) VALUES (?, ?, ?, ?)",
            (wh_id, url, json.dumps(events), now),
        )
        await self.conn.commit()
        return {"id": wh_id, "url": url, "events": events, "created_at": now}

    async def get_webhooks(self):
        """Return all registered webhooks."""
        import json
        cursor = await self.conn.execute("SELECT * FROM webhooks ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["events"] = json.loads(d["events"])
            results.append(d)
        return results

    async def get_webhook(self, wh_id):
        """Return a single webhook by id."""
        import json
        cursor = await self.conn.execute("SELECT * FROM webhooks WHERE id = ?", (wh_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["events"] = json.loads(d["events"])
        return d

    async def delete_webhook(self, wh_id):
        """Delete a webhook by id. Returns True if it existed."""
        cursor = await self.conn.execute("DELETE FROM webhooks WHERE id = ?", (wh_id,))
        await self.conn.commit()
        return cursor.rowcount > 0

    async def count_webhooks(self):
        """Return total number of registered webhooks."""
        cursor = await self.conn.execute("SELECT COUNT(*) FROM webhooks")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def close(self):
        if self.conn:
            await self.conn.close()
