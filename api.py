from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from db import Database

db = Database()


@asynccontextmanager
async def lifespan(app):
    await db.init()
    yield
    await db.close()


app = FastAPI(title="SentinelNet", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sentinelnet"}


@app.get("/api/scores")
async def list_scores():
    scores = await db.get_all_scores()
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    return {
        "scores": scores,
        "total": len(scores),
        "verdicts": verdicts,
    }


@app.get("/trust/{agent_id}")
async def get_trust(agent_id: int):
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    return score


@app.get("/trust/graph/{agent_id}")
async def get_trust_graph(agent_id: int):
    edges = await db.get_edges(agent_id)
    return {"agent_id": agent_id, "neighbors": edges}


@app.get("/dashboard")
async def dashboard():
    return FileResponse("dashboard/index.html")


@app.get("/api/stats")
async def stats():
    scores = await db.get_all_scores()
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    return {
        "agents_scored": len(scores),
        "avg_trust_score": round(sum(s["trust_score"] for s in scores) / len(scores), 1) if scores else 0,
        "verdicts": verdicts,
    }
