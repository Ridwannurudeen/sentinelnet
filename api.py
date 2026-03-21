import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
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


def _explain_score(score_dict: dict) -> dict:
    """Generate human-readable explanation for each dimension."""
    explanations = []
    s = score_dict

    lon = s.get("longevity", 0)
    if lon >= 70:
        explanations.append(f"Established wallet with strong history (longevity: {lon}/100)")
    elif lon >= 40:
        explanations.append(f"Moderately aged wallet (longevity: {lon}/100)")
    else:
        explanations.append(f"New or very young wallet (longevity: {lon}/100)")

    act = s.get("activity", 0)
    if act >= 70:
        explanations.append(f"High transaction activity and engagement (activity: {act}/100)")
    elif act >= 40:
        explanations.append(f"Moderate on-chain activity (activity: {act}/100)")
    else:
        explanations.append(f"Low transaction activity — limited on-chain presence (activity: {act}/100)")

    cp = s.get("counterparty", 0)
    if cp >= 70:
        explanations.append(f"Interacts primarily with verified counterparties (counterparty: {cp}/100)")
    elif cp >= 40:
        explanations.append(f"Mixed counterparty quality — some unverified interactions (counterparty: {cp}/100)")
    else:
        explanations.append(f"High ratio of flagged or unverified counterparties (counterparty: {cp}/100)")

    cr = s.get("contract_risk", 0)
    if cr >= 70:
        explanations.append(f"Clean contract interactions — no malicious exposure (risk: {cr}/100)")
    elif cr >= 40:
        explanations.append(f"Some unverified contract interactions detected (risk: {cr}/100)")
    else:
        explanations.append(f"Significant malicious or unverified contract exposure (risk: {cr}/100)")

    ai = s.get("agent_identity", 0)
    if ai >= 70:
        explanations.append(f"Rich ERC-8004 metadata and positive on-chain reputation (identity: {ai}/100)")
    elif ai >= 40:
        explanations.append(f"Partial ERC-8004 registration metadata (identity: {ai}/100)")
    else:
        explanations.append(f"Minimal or no ERC-8004 metadata — bare registration (identity: {ai}/100)")

    # Contagion
    contagion = s.get("contagion_adjustment", 0)
    if contagion and contagion != 0:
        if contagion < 0:
            explanations.append(f"Trust contagion: score reduced by {abs(contagion)} due to interactions with low-trust agents")
        else:
            explanations.append(f"Trust contagion: score boosted by {contagion} from interactions with high-trust agents")

    if s.get("sybil_flagged"):
        explanations.append("SYBIL WARNING: Agent flagged as part of a coordinated cluster (-20 penalty applied)")

    if s.get("is_stale"):
        explanations.append(f"Score is stale — last scored {s.get('decay_days', '?')} days ago, decay applied")

    verdict = s.get("verdict", "UNSCORED")
    trust = s.get("trust_score", 0)
    if verdict == "TRUST":
        summary = f"Agent is TRUSTED with a score of {trust}. Safe for interaction."
    elif verdict == "CAUTION":
        summary = f"Agent requires CAUTION with a score of {trust}. Proceed with limits."
    else:
        summary = f"Agent is REJECTED with a score of {trust}. Avoid interaction."

    return {"summary": summary, "factors": explanations}


def _badge_svg(agent_id: int, score: int, verdict: str) -> str:
    """Generate an SVG trust badge."""
    colors = {"TRUST": "#00dd77", "CAUTION": "#ffaa22", "REJECT": "#ff3344"}
    bg = colors.get(verdict, "#555570")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="32" viewBox="0 0 200 32">
  <rect width="200" height="32" rx="6" fill="#0f0f1a"/>
  <rect x="1" y="1" width="198" height="30" rx="5" fill="none" stroke="{bg}" stroke-width="1" opacity="0.4"/>
  <text x="10" y="21" font-family="system-ui,sans-serif" font-size="12" fill="#8888aa">SentinelNet</text>
  <rect x="95" y="4" width="100" height="24" rx="4" fill="{bg}" opacity="0.15"/>
  <text x="105" y="21" font-family="system-ui,sans-serif" font-size="12" font-weight="700" fill="{bg}">{verdict} {score}</text>
</svg>'''


@asynccontextmanager
async def lifespan(app):
    await db.init()
    yield
    await db.close()


app = FastAPI(
    title="SentinelNet",
    version="2.1.0",
    description="Autonomous reputation immune system for ERC-8004 agents on Base. "
                "5-dimensional trust scoring with trust contagion, sybil detection, "
                "threat intelligence, IPFS evidence, and EAS attestations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Pages ───

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing():
    return FileResponse("dashboard/landing.html")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return FileResponse("dashboard/index.html")


@app.get("/agent/{agent_id}", response_class=HTMLResponse, include_in_schema=False)
async def agent_profile(agent_id: int):
    return FileResponse("dashboard/agent.html")


@app.get("/docs-guide", response_class=HTMLResponse, include_in_schema=False)
async def integration_docs():
    return FileResponse("dashboard/docs.html")


@app.get("/graph", response_class=HTMLResponse, include_in_schema=False)
async def graph_page():
    return FileResponse("dashboard/graph.html")


# ─── API ───

@app.get("/api/health", tags=["System"])
async def health():
    """Health check endpoint. Returns service status and version."""
    return {"status": "ok", "service": "sentinelnet", "version": "2.1.0"}


@app.get("/api/scores", tags=["Scores"])
async def list_scores(apply_decay: bool = Query(True, description="Apply time-based trust decay")):
    """Get all scored agents with verdict breakdown and sybil count."""
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


@app.get("/api/stats", tags=["Scores"])
async def stats():
    """Aggregate trust statistics across all scored agents."""
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
    contagion_count = sum(1 for s in scores if s.get("contagion_adjustment", 0) != 0)

    buckets = {"0-19": 0, "20-39": 0, "40-54": 0, "55-74": 0, "75-100": 0}
    for ts in trust_scores:
        if ts >= 75: buckets["75-100"] += 1
        elif ts >= 55: buckets["55-74"] += 1
        elif ts >= 40: buckets["40-54"] += 1
        elif ts >= 20: buckets["20-39"] += 1
        else: buckets["0-19"] += 1

    return {
        "agents_scored": len(scores),
        "avg_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
        "min_trust_score": min(trust_scores) if trust_scores else 0,
        "max_trust_score": max(trust_scores) if trust_scores else 0,
        "verdicts": verdicts,
        "distribution": buckets,
        "sybil_flagged": sybil_count,
        "stale_scores": stale_count,
        "contagion_affected": contagion_count,
    }


@app.get("/trust/{agent_id}", tags=["Trust"])
async def get_trust(agent_id: int):
    """Get trust score for a specific agent with decay and explanation."""
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    score = _apply_decay(score)
    score["explanation"] = _explain_score(score)
    return score


@app.get("/trust/{agent_id}/history", tags=["Trust"])
async def get_trust_history(agent_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get scoring history for an agent to see trust trends over time."""
    history = await db.get_score_history(agent_id, limit=limit)
    if not history:
        raise HTTPException(404, f"No history for agent {agent_id}")
    return {"agent_id": agent_id, "history": history, "entries": len(history)}


@app.get("/trust/graph/{agent_id}", tags=["Trust"])
async def get_trust_graph(agent_id: int):
    """Get an agent's counterparty trust neighborhood."""
    edges = await db.get_edges(agent_id)
    return {"agent_id": agent_id, "neighbors": edges, "total_neighbors": len(edges)}


@app.post("/trust/batch", tags=["Trust"])
async def batch_trust(request: Request):
    """Query trust scores for multiple agents at once. Body: {"agent_ids": [1, 2, 3, ...]}"""
    body = await request.json()
    agent_ids = body.get("agent_ids", [])
    if not agent_ids or len(agent_ids) > 100:
        raise HTTPException(400, "Provide 1-100 agent_ids")
    results = {}
    for aid in agent_ids:
        score = await db.get_score(aid)
        if score:
            score = _apply_decay(score)
            results[str(aid)] = score
        else:
            results[str(aid)] = None
    return {"results": results, "queried": len(agent_ids), "found": sum(1 for v in results.values() if v)}


@app.get("/badge/{agent_id}.svg", tags=["Embed"], response_class=Response)
async def trust_badge(agent_id: int):
    """Get an embeddable SVG trust badge for an agent."""
    score = await db.get_score(agent_id)
    if not score:
        svg = _badge_svg(agent_id, 0, "UNSCORED")
    else:
        score = _apply_decay(score)
        svg = _badge_svg(agent_id, score["trust_score"], score["verdict"])
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=300"},
    )


# ─── Threat Intelligence ───

@app.get("/api/threats", tags=["Threats"])
async def get_threats(limit: int = Query(50, ge=1, le=200)):
    """Real-time threat intelligence feed. Returns recent sybil detections,
    trust degradations, and contagion events."""
    threats = await db.get_threats(limit=limit)
    return {"threats": threats, "count": len(threats)}


# ─── Graph Visualization ───

@app.get("/api/graph-data", tags=["Graph"])
async def graph_data():
    """Get full agent interaction graph for D3.js visualization.
    Returns nodes (agents) and links (interactions)."""
    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]
    edges = await db.get_all_edges()

    # Build wallet→agent lookup
    wallet_to_agent = {}
    for s in scores:
        wallet_to_agent[s["wallet"].lower()] = s["agent_id"]

    # Nodes
    nodes = []
    for s in scores:
        nodes.append({
            "id": s["agent_id"],
            "wallet": s["wallet"][:10] + "...",
            "score": s["trust_score"],
            "verdict": s.get("verdict", "UNSCORED"),
            "sybil": bool(s.get("sybil_flagged")),
            "contagion": s.get("contagion_adjustment", 0),
            "identity": s.get("agent_identity", 0),
        })

    # Links (only between scored agents)
    links = []
    seen_links = set()
    for e in edges:
        source = e["agent_id"]
        target_wallet = e["counterparty"].lower()
        target = wallet_to_agent.get(target_wallet)
        if target and target != source:
            key = (min(source, target), max(source, target))
            if key not in seen_links:
                seen_links.add(key)
                links.append({
                    "source": source,
                    "target": target,
                    "weight": e.get("interaction_count", 1),
                })

    return {"nodes": nodes, "links": links}


# ─── Admin ───

# Agent reference set by main.py at startup
_agent_ref = None


@app.post("/api/score/{agent_id}", tags=["Admin"])
async def trigger_score(agent_id: int):
    """Trigger on-demand scoring for a specific agent. Used for self-scoring and manual rescores."""
    if not _agent_ref:
        raise HTTPException(503, "Agent not initialized yet")
    try:
        result = await _agent_ref.analyze_agent(agent_id)
        if not result:
            raise HTTPException(404, f"Could not score agent {agent_id} (no wallet found)")
        return {
            "agent_id": agent_id,
            "trust_score": result.trust_score,
            "verdict": result.verdict,
            "status": "scored",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")
