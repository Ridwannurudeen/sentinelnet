import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from db import Database
from agent.trust_engine import TrustEngine, DECAY_LAMBDA

db = Database()
engine = TrustEngine()


def _apply_decay(score_dict: dict) -> dict:
    """Apply trust decay based on time since last scoring."""
    scored_at = score_dict.get("scored_at")
    if not scored_at:
        return score_dict
    try:
        scored_dt = datetime.fromisoformat(scored_at)
        if scored_dt.tzinfo is None:
            scored_dt = scored_dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - scored_dt).total_seconds() / 86400
        if days > 0.01:
            base = score_dict["trust_score"]
            decayed = engine.apply_decay(base, days)
            score_dict = dict(score_dict)
            score_dict["trust_score_raw"] = base
            score_dict["trust_score"] = decayed
            score_dict["decay_days"] = round(days, 2)
            score_dict["verdict"] = engine._verdict(decayed)
            score_dict["is_stale"] = engine.is_stale(days)
    except Exception:
        pass
    return score_dict


@asynccontextmanager
async def lifespan(app):
    await db.init()
    yield
    await db.close()


app = FastAPI(title="SentinelNet", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sentinelnet", "version": "2.0.0"}


@app.get("/api/scores")
async def list_scores(apply_decay: bool = Query(True, description="Apply time-based trust decay")):
    scores = await db.get_all_scores()
    if apply_decay:
        scores = [_apply_decay(s) for s in scores]
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    sybil_count = sum(1 for s in scores if s.get("sybil_flagged"))
    return {
        "scores": scores,
        "total": len(scores),
        "verdicts": verdicts,
        "sybil_flagged": sybil_count,
    }


@app.get("/trust/{agent_id}")
async def get_trust(agent_id: int):
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    return _apply_decay(score)


@app.get("/trust/{agent_id}/history")
async def get_trust_history(agent_id: int, limit: int = Query(50, ge=1, le=200)):
    history = await db.get_score_history(agent_id, limit=limit)
    if not history:
        raise HTTPException(404, f"No history for agent {agent_id}")
    return {"agent_id": agent_id, "history": history, "entries": len(history)}


@app.get("/trust/graph/{agent_id}")
async def get_trust_graph(agent_id: int):
    edges = await db.get_edges(agent_id)
    return {"agent_id": agent_id, "neighbors": edges, "total_neighbors": len(edges)}


@app.get("/dashboard")
async def dashboard():
    return FileResponse("dashboard/index.html")


@app.get("/api/stats")
async def stats():
    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    trust_scores = [s["trust_score"] for s in scores]
    sybil_count = sum(1 for s in scores if s.get("sybil_flagged"))
    stale_count = sum(1 for s in scores if s.get("is_stale"))
    return {
        "agents_scored": len(scores),
        "avg_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
        "min_trust_score": min(trust_scores) if trust_scores else 0,
        "max_trust_score": max(trust_scores) if trust_scores else 0,
        "verdicts": verdicts,
        "sybil_flagged": sybil_count,
        "stale_scores": stale_count,
    }
