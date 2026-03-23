import asyncio
import hashlib
import hmac
import ipaddress
import json as json_module
import logging
import math
import os
import random
import secrets
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Path, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from web3 import Web3
from db import Database
from config import Settings
from agent.trust_engine import TrustEngine, DECAY_LAMBDA

db = Database()
engine = TrustEngine()
logger = logging.getLogger("sentinelnet.api")
_settings = Settings()
_api_keys: dict = {}  # key -> {email, created_at} — dynamically registered keys

# Agent ID bounds (ERC-8004 uses uint256 but realistic IDs are much smaller)
MAX_AGENT_ID = 2**32  # ~4 billion, well above current registry size


def _validate_agent_id(agent_id: int) -> None:
    """Raise 400 if agent_id is out of valid range."""
    if agent_id < 0 or agent_id > MAX_AGENT_ID:
        raise HTTPException(400, f"Invalid agent_id: must be between 0 and {MAX_AGENT_ID}")


# Anomaly detection cache (TTL-based to avoid recomputing 2000+ anomalies per request)
_anomaly_cache: dict = {"anomalies": None, "checked": 0, "ts": 0}
_ANOMALY_CACHE_TTL = 30  # seconds


def _is_valid_api_key(key: str) -> bool:
    """Check if an API key is valid (either from config or dynamically registered)."""
    if key in _api_keys:
        return True
    configured = _settings.API_KEYS.strip()
    if configured:
        return key in [k.strip() for k in configured.split(",") if k.strip()]
    return False


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
        explanations.append(f"Low transaction activity -- limited on-chain presence (activity: {act}/100)")

    cp = s.get("counterparty", 0)
    if cp >= 70:
        explanations.append(f"Interacts primarily with verified counterparties (counterparty: {cp}/100)")
    elif cp >= 40:
        explanations.append(f"Mixed counterparty quality -- some unverified interactions (counterparty: {cp}/100)")
    else:
        explanations.append(f"High ratio of flagged or unverified counterparties (counterparty: {cp}/100)")

    cr = s.get("contract_risk", 0)
    if cr >= 70:
        explanations.append(f"Clean contract interactions -- no malicious exposure (risk: {cr}/100)")
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
        explanations.append(f"Minimal or no ERC-8004 metadata -- bare registration (identity: {ai}/100)")

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
        explanations.append(f"Score is stale -- last scored {s.get('decay_days', '?')} days ago, decay applied")

    verdict = s.get("verdict", "UNSCORED")
    trust = s.get("trust_score", 0)
    if verdict == "TRUST":
        summary = f"Agent is TRUSTED with a score of {trust}. Safe for interaction."
    elif verdict == "CAUTION":
        summary = f"Agent requires CAUTION with a score of {trust}. Proceed with limits."
    else:
        summary = f"Agent is REJECTED with a score of {trust}. Avoid interaction."

    # Recovery recommendations for CAUTION/REJECT agents
    recommendations = _recovery_recommendations(s)

    result = {"summary": summary, "factors": explanations}
    if recommendations:
        result["recovery"] = recommendations
    return result


def _recovery_recommendations(s: dict) -> list:
    """Generate actionable recommendations for agents to improve their trust score."""
    verdict = s.get("verdict", "UNSCORED")
    if verdict == "TRUST":
        return []

    recs = []
    lon = s.get("longevity", 0)
    act = s.get("activity", 0)
    cp = s.get("counterparty", 0)
    cr = s.get("contract_risk", 0)
    ai = s.get("agent_identity", 0)

    # Find weakest dimensions and give specific advice
    dims = [("longevity", lon), ("activity", act), ("counterparty", cp),
            ("contract_risk", cr), ("agent_identity", ai)]
    dims.sort(key=lambda x: x[1])

    for name, val in dims:
        if val >= 70:
            continue
        if name == "longevity" and val < 70:
            if val < 30:
                recs.append({"dimension": "longevity", "score": val, "priority": "high",
                             "action": "Wallet is very new. Maintain consistent on-chain activity over the next 30+ days to build history."})
            else:
                recs.append({"dimension": "longevity", "score": val, "priority": "medium",
                             "action": "Continue regular on-chain activity. Score improves naturally as wallet ages past 90 days."})
        elif name == "activity" and val < 70:
            if val < 30:
                recs.append({"dimension": "activity", "score": val, "priority": "high",
                             "action": "Very low on-chain activity. Execute regular transactions on Base -- interact with verified protocols like Uniswap, USDC, or WETH."})
            else:
                recs.append({"dimension": "activity", "score": val, "priority": "medium",
                             "action": "Increase transaction frequency and maintain an ETH balance on Base. Active 60%+ of days maximizes this dimension."})
        elif name == "counterparty" and val < 70:
            if val < 30:
                recs.append({"dimension": "counterparty", "score": val, "priority": "high",
                             "action": "Interact with verified protocols (Uniswap, USDC, WETH). Avoid transactions with flagged or unknown addresses."})
            else:
                recs.append({"dimension": "counterparty", "score": val, "priority": "medium",
                             "action": "Diversify interactions -- engage with 30+ unique verified counterparties to maximize diversity bonus."})
        elif name == "contract_risk" and val < 70:
            if val < 30:
                recs.append({"dimension": "contract_risk", "score": val, "priority": "high",
                             "action": "High exposure to unverified or malicious contracts detected. Only interact with audited, verified protocols."})
            else:
                recs.append({"dimension": "contract_risk", "score": val, "priority": "medium",
                             "action": "Reduce interactions with unverified contracts. Stick to established protocols with verified source code."})
        elif name == "agent_identity" and val < 70:
            if val < 30:
                recs.append({"dimension": "agent_identity", "score": val, "priority": "high",
                             "action": "Register complete ERC-8004 metadata: name, description, image, service endpoint, operator, and capabilities. Request positive reputation feedback from other agents."})
            else:
                recs.append({"dimension": "agent_identity", "score": val, "priority": "medium",
                             "action": "Add more ERC-8004 metadata fields and build positive on-chain reputation through reliable service."})

    if s.get("sybil_flagged"):
        recs.insert(0, {"dimension": "sybil", "score": 0, "priority": "critical",
                        "action": "Agent is flagged as part of a sybil cluster (-20 penalty). Use a unique wallet not shared with other agents and avoid closed interaction loops."})

    contagion = s.get("contagion_adjustment", 0)
    if contagion and contagion < -3:
        recs.append({"dimension": "contagion", "score": contagion, "priority": "high",
                     "action": f"Score reduced by {abs(contagion)} from trust contagion. Stop interacting with low-trust/REJECT agents to prevent further score erosion."})

    return recs


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


RESCORE_INTERVAL_SECONDS = 60
RESCORE_BATCH_SIZE = 5


async def _periodic_rescore_loop():
    """Background task: every 60s, pick 5 random scored agents and re-score them.

    This keeps the WebSocket /ws/scores feed populated with fresh data.
    Uses _agent_ref set by main.py — skips silently if agent not ready.
    """
    await asyncio.sleep(10)  # Let startup settle
    while True:
        try:
            if _agent_ref is None:
                logger.info("Periodic rescore: agent not ready yet, waiting...")
                await asyncio.sleep(RESCORE_INTERVAL_SECONDS)
                continue

            all_scores = await db.get_all_scores()
            if not all_scores:
                logger.info("Periodic rescore: no scored agents in DB, skipping cycle")
                await asyncio.sleep(RESCORE_INTERVAL_SECONDS)
                continue

            agent_ids = [s["agent_id"] for s in all_scores]
            batch = random.sample(agent_ids, min(RESCORE_BATCH_SIZE, len(agent_ids)))
            logger.info(f"Periodic rescore: re-scoring {len(batch)} agents: {batch}")

            for agent_id in batch:
                try:
                    await _agent_ref.analyze_agent(agent_id)
                except Exception as e:
                    logger.warning(f"Periodic rescore: failed to score agent {agent_id}: {e}")

        except Exception as e:
            logger.error(f"Periodic rescore loop error: {e}", exc_info=True)

        await asyncio.sleep(RESCORE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app):
    await db.init()
    rescore_task = asyncio.create_task(_periodic_rescore_loop())
    yield
    rescore_task.cancel()
    try:
        await rescore_task
    except asyncio.CancelledError:
        pass
    await db.close()


app = FastAPI(
    title="SentinelNet",
    version="2.2.0",
    description="Autonomous reputation immune system for ERC-8004 agents on Base. "
                "5-dimensional trust scoring with trust contagion, sybil detection, "
                "threat intelligence, and IPFS evidence.",
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sentinelnet.gudman.xyz",
        "http://localhost:3000",
        "http://localhost:8004",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ─── Security Headers Middleware ───


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─── API Key Authentication Middleware ───

# Paths that bypass API key authentication
_AUTH_SKIP_EXACT = frozenset({
    "/", "/dashboard", "/marketplace", "/graph", "/leaderboard", "/methodology", "/demo",
    "/docs-guide", "/api/health", "/docs", "/swagger", "/openapi.json", "/redoc", "/metrics",
})
_AUTH_SKIP_PREFIXES = ("/_next/", "/badge/", "/ws/", "/agent/")


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Enforces API key authentication on mutating API routes.

    GET requests are always allowed (read-only, safe for public demo).
    POST/DELETE require a valid API key via X-API-Key header or api_key query param.
    Skips auth entirely for page routes, docs, health, badges, static assets,
    WebSocket connections, and the key self-registration endpoint.
    """

    async def dispatch(self, request: Request, call_next):
        # Always allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # Skip auth for page routes, docs, health, and static assets
        if path in _AUTH_SKIP_EXACT:
            return await call_next(request)
        for prefix in _AUTH_SKIP_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        # /agent/{id} page route
        if path.startswith("/agent/") and not path.startswith("/api/"):
            return await call_next(request)
        # Badge SVGs
        if path.endswith(".svg") and "/badge/" in path:
            return await call_next(request)
        # Key self-registration (rate-limited separately)
        if path == "/api/keys" and request.method == "POST":
            return await call_next(request)

        # GET requests are read-only — allow without auth for public demo
        if request.method == "GET":
            return await call_next(request)

        # POST/DELETE require API key authentication
        api_key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing API key", "docs": "/docs-guide#authentication"},
            )

        if not _is_valid_api_key(api_key):
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key"},
            )

        return await call_next(request)


app.add_middleware(APIKeyAuthMiddleware)


# ─── Pages ───

_next_dir = os.path.join("landing", "out", "_next")
if os.path.isdir(_next_dir):
    app.mount("/_next", StaticFiles(directory=_next_dir), name="next-static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing():
    nextjs_index = os.path.join("landing", "out", "index.html")
    if os.path.isfile(nextjs_index):
        return FileResponse(nextjs_index)
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


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def docs_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/docs-guide", status_code=301)


@app.get("/graph", response_class=HTMLResponse, include_in_schema=False)
async def graph_page():
    return FileResponse("dashboard/graph.html")


@app.get("/leaderboard", response_class=HTMLResponse, include_in_schema=False)
async def leaderboard_page():
    return FileResponse("dashboard/leaderboard.html")


@app.get("/methodology", response_class=HTMLResponse, include_in_schema=False)
async def methodology_page():
    return FileResponse("dashboard/methodology.html")


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def demo_page():
    return FileResponse("dashboard/demo.html")


# ─── API ───

@app.get("/api/health", tags=["System"])
async def health():
    """Health check endpoint. Returns service status and version."""
    return {"status": "ok", "service": "sentinelnet", "version": "2.2.0"}


@app.get("/api/scores", tags=["Scores"])
async def list_scores(
    apply_decay: bool = Query(True, description="Apply time-based trust decay"),
    limit: int = Query(100, ge=1, le=1000, description="Max agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to skip"),
):
    """Get scored agents with verdict breakdown and sybil count (paginated)."""
    scores = await db.get_all_scores()
    if apply_decay:
        scores = [_apply_decay(s) for s in scores]
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    sybil_count = sum(1 for s in scores if s.get("sybil_flagged"))
    total = len(scores)
    page = scores[offset:offset + limit]
    return {
        "scores": page,
        "total": total,
        "returned": len(page),
        "limit": limit,
        "offset": offset,
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

    # Ecosystem health: 40% avg score + 30% trust ratio + 30% inverse sybil ratio
    total = len(scores)
    avg_s = sum(trust_scores) / total if total else 0
    trust_pct = (verdicts["TRUST"] / total) if total else 0
    sybil_pct = (sybil_count / total) if total else 0
    ecosystem_health = round(avg_s * 0.4 + trust_pct * 100 * 0.3 + (1 - sybil_pct) * 100 * 0.3) if total else 0

    return {
        "agents_scored": total,
        "avg_trust_score": round(avg_s, 1),
        "min_trust_score": min(trust_scores) if trust_scores else 0,
        "max_trust_score": max(trust_scores) if trust_scores else 0,
        "verdicts": verdicts,
        "distribution": buckets,
        "ecosystem_health": ecosystem_health,
        "sybil_flagged": sybil_count,
        "stale_scores": stale_count,
        "contagion_affected": contagion_count,
    }


# ─── Agent Comparison (must be before /trust/{agent_id} to avoid route conflict) ───

@app.get("/trust/compare", tags=["Trust"])
async def compare_agents(agents: str = Query(..., description="Comma-separated agent IDs (max 10)")):
    """Compare trust scores across multiple agents side-by-side."""
    parts = agents.split(",")
    if len(parts) > 10:
        raise HTTPException(400, "Maximum 10 agents for comparison")
    try:
        agent_ids = [int(x.strip()) for x in parts]
    except ValueError:
        raise HTTPException(400, "Provide comma-separated integer agent IDs")

    results = []
    for aid in agent_ids:
        score = await db.get_score(aid)
        if score:
            score = _apply_decay(score)
            results.append({
                "agent_id": aid,
                "trust_score": score["trust_score"],
                "verdict": score["verdict"],
                "dimensions": {
                    "longevity": score["longevity"],
                    "activity": score["activity"],
                    "counterparty": score["counterparty"],
                    "contract_risk": score["contract_risk"],
                    "agent_identity": score.get("agent_identity", 0),
                },
                "sybil_flagged": bool(score.get("sybil_flagged")),
                "contagion_adjustment": score.get("contagion_adjustment", 0),
            })
        else:
            results.append({"agent_id": aid, "error": "Not scored"})

    scored = [r for r in results if "trust_score" in r]
    scored.sort(key=lambda x: x["trust_score"], reverse=True)
    for i, r in enumerate(scored):
        r["rank"] = i + 1

    return {"agents": results, "compared": len(agent_ids), "found": len(scored)}


@app.get("/trust/{agent_id}", tags=["Trust"])
async def get_trust(agent_id: int):
    """Get trust score for a specific agent with decay and explanation."""
    _validate_agent_id(agent_id)
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    score = _apply_decay(score)
    score["explanation"] = _explain_score(score)
    return score


@app.get("/trust/{agent_id}/history", tags=["Trust"])
async def get_trust_history(agent_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get scoring history for an agent to see trust trends over time."""
    _validate_agent_id(agent_id)
    history = await db.get_score_history(agent_id, limit=limit)
    if not history:
        raise HTTPException(404, f"No history for agent {agent_id}")
    return {"agent_id": agent_id, "history": history, "entries": len(history)}


@app.get("/trust/graph/{agent_id}", tags=["Trust"])
async def get_trust_graph(agent_id: int):
    """Get an agent's counterparty trust neighborhood."""
    _validate_agent_id(agent_id)
    edges = await db.get_edges(agent_id)
    return {"agent_id": agent_id, "neighbors": edges, "total_neighbors": len(edges)}


@app.post("/trust/batch", tags=["Trust"])
async def batch_trust(request: Request):
    """Query trust scores for multiple agents at once. Body: {"agent_ids": [1, 2, 3, ...]}"""
    body = await request.json()
    agent_ids = body.get("agent_ids", [])
    if not agent_ids or len(agent_ids) > 100:
        raise HTTPException(400, "Provide 1-100 agent_ids")
    if not all(isinstance(x, int) for x in agent_ids):
        raise HTTPException(400, "All agent_ids must be integers")
    for aid in agent_ids:
        _validate_agent_id(aid)
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


# ─── Evidence ───

@app.get("/evidence/{agent_id}", tags=["Evidence"])
async def get_evidence(agent_id: int, request: Request):
    """Verifiable evidence JSON for an agent's trust score.
    Content-addressed: if ?hash= is provided, the response content hash is verified against it."""
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"No evidence for agent {agent_id}")
    evidence = {
        "agent_id": score["agent_id"],
        "wallet": score["wallet"],
        "trust_score": score["trust_score"],
        "breakdown": {
            "longevity": score["longevity"],
            "activity": score["activity"],
            "counterparty_quality": score["counterparty"],
            "contract_risk": score["contract_risk"],
            "agent_identity": score.get("agent_identity", 0),
        },
        "verdict": score["verdict"],
        "sybil_flagged": bool(score.get("sybil_flagged")),
        "contagion_adjustment": score.get("contagion_adjustment", 0),
        "chains_analyzed": ["base", "ethereum"],
        "scorer": "sentinelnet-v1",
        "scored_at": score["scored_at"],
    }
    # Verify content hash if provided
    expected_hash = request.query_params.get("hash", "")
    if expected_hash:
        content_hash = hashlib.sha256(json_module.dumps(evidence).encode()).hexdigest()
        evidence["content_hash"] = content_hash[:16]
        evidence["hash_match"] = content_hash.startswith(expected_hash)
    return evidence


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


# ─── On-Chain Verification ───

_w3 = None
_trustgate = None

TRUSTGATE_ABI_VIEWS = [
    {"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getTrustRecord","outputs":[{"internalType":"uint8","name":"score","type":"uint8"},{"internalType":"uint8","name":"verdict","type":"uint8"},{"internalType":"uint40","name":"updatedAt","type":"uint40"},{"internalType":"string","name":"evidenceURI","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"isTrusted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalScored","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getVerdict","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
]

def _get_trustgate():
    global _w3, _trustgate
    if _trustgate:
        return _trustgate
    if not _settings.TRUSTGATE_CONTRACT:
        return None
    _w3 = Web3(Web3.HTTPProvider(_settings.BASE_RPC_URL))
    _trustgate = _w3.eth.contract(
        address=Web3.to_checksum_address(_settings.TRUSTGATE_CONTRACT),
        abi=TRUSTGATE_ABI_VIEWS,
    )
    return _trustgate


@app.get("/api/trustgate/{agent_id}", tags=["On-Chain"])
async def get_trustgate_record(agent_id: int):
    """Read an agent's trust record directly from the TrustGate contract on Base."""
    gate = _get_trustgate()
    if not gate:
        raise HTTPException(503, "TrustGate contract not configured")
    try:
        score, verdict_num, updated_at, evidence_uri = await asyncio.to_thread(
            gate.functions.getTrustRecord(agent_id).call
        )
        verdict_map = {0: "UNSCORED", 1: "TRUST", 2: "CAUTION", 3: "REJECT"}
        return {
            "agent_id": agent_id,
            "on_chain": True,
            "score": score,
            "verdict": verdict_map.get(verdict_num, "UNSCORED"),
            "updated_at": updated_at,
            "evidence_uri": evidence_uri,
            "contract": _settings.TRUSTGATE_CONTRACT,
            "explorer": f"https://basescan.org/address/{_settings.TRUSTGATE_CONTRACT}",
        }
    except Exception:
        raise HTTPException(500, "On-chain read failed")


@app.get("/api/contracts", tags=["On-Chain"])
async def list_contracts():
    """List all deployed SentinelNet contracts with addresses and explorer links."""
    contracts = [
        {
            "name": "SentinelNetStaking",
            "address": _settings.STAKING_CONTRACT,
            "explorer": f"https://basescan.org/address/{_settings.STAKING_CONTRACT}" if _settings.STAKING_CONTRACT else None,
            "chain": "Base",
        },
    ]
    if _settings.TRUSTGATE_CONTRACT:
        contracts.append({
            "name": "TrustGate",
            "address": _settings.TRUSTGATE_CONTRACT,
            "explorer": f"https://basescan.org/address/{_settings.TRUSTGATE_CONTRACT}",
            "chain": "Base",
        })

    result = {
        "contracts": contracts,
        "registries": {
            "identity": {"address": _settings.IDENTITY_REGISTRY, "explorer": f"https://basescan.org/address/{_settings.IDENTITY_REGISTRY}"},
            "reputation": {"address": _settings.REPUTATION_REGISTRY, "explorer": f"https://basescan.org/address/{_settings.REPUTATION_REGISTRY}"},
        },
    }

    if _settings.EAS_SCHEMA_UID:
        result["eas"] = {
            "schema_uid": _settings.EAS_SCHEMA_UID,
            "explorer": f"https://base.easscan.org/schema/view/{_settings.EAS_SCHEMA_UID}",
        }

    # TrustGate on-chain stats
    gate = _get_trustgate()
    if gate:
        try:
            total = await asyncio.to_thread(gate.functions.totalScored().call)
            result["trustgate_stats"] = {"total_scored_on_chain": total}
        except Exception:
            pass

    return result


@app.get("/api/eas/{agent_id}", tags=["On-Chain"])
async def get_eas_attestation(agent_id: int):
    """Get EAS attestation info for an agent."""
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    uid = score.get("attestation_uid", "")
    if not uid:
        return {
            "agent_id": agent_id,
            "attested": False,
            "message": "No EAS attestation found for this agent",
        }
    return {
        "agent_id": agent_id,
        "attested": True,
        "attestation_uid": uid,
        "explorer": f"https://base.easscan.org/attestation/view/{uid}" if uid.startswith("0x") else None,
        "schema_uid": _settings.EAS_SCHEMA_UID or None,
    }


# ─── Simulation ───

@app.post("/api/simulate", tags=["Simulation"])
async def simulate_interaction(request: Request):
    """Predict how Agent A's score would change if they interact with Agent B.
    Body: {"agent_id": 123, "interact_with": 456}"""
    body = await request.json()
    agent_a = body.get("agent_id")
    agent_b = body.get("interact_with")
    if not agent_a or not agent_b:
        raise HTTPException(400, "Provide agent_id and interact_with")
    if not isinstance(agent_a, int) or not isinstance(agent_b, int):
        raise HTTPException(400, "agent_id and interact_with must be integers")

    score_a = await db.get_score(agent_a)
    score_b = await db.get_score(agent_b)
    if not score_a:
        raise HTTPException(404, f"Agent {agent_a} not scored yet")
    if not score_b:
        raise HTTPException(404, f"Agent {agent_b} not scored yet")

    score_a = _apply_decay(score_a)
    score_b = _apply_decay(score_b)
    a_score = score_a["trust_score"]
    b_score = score_b["trust_score"]

    # Simulate contagion effect: how B's trust level would affect A
    if b_score >= 55:  # TRUST
        contagion_effect = min(round((b_score - 55) / 45 * 10), 10)
        direction = "positive"
        message = f"Interacting with TRUSTED Agent #{agent_b} (score {b_score}) would boost your score by up to +{contagion_effect} points via trust contagion."
    elif b_score >= 40:  # CAUTION
        contagion_effect = 0
        direction = "neutral"
        message = f"Interacting with CAUTION Agent #{agent_b} (score {b_score}) would have minimal impact on your score."
    else:  # REJECT
        contagion_effect = max(round((40 - b_score) / 40 * -15), -15)
        direction = "negative"
        message = f"Interacting with REJECTED Agent #{agent_b} (score {b_score}) could reduce your score by up to {contagion_effect} points via negative contagion."

    projected = max(0, min(100, a_score + contagion_effect))
    projected_verdict = engine._verdict(projected)

    # Check if verdict would change
    verdict_change = None
    if projected_verdict != score_a["verdict"]:
        verdict_change = {"from": score_a["verdict"], "to": projected_verdict}

    return {
        "agent_id": agent_a,
        "current_score": a_score,
        "current_verdict": score_a["verdict"],
        "interact_with": agent_b,
        "target_score": b_score,
        "target_verdict": score_b["verdict"],
        "predicted_contagion": contagion_effect,
        "predicted_score": projected,
        "predicted_verdict": projected_verdict,
        "direction": direction,
        "verdict_change": verdict_change,
        "message": message,
        "warning": "This is a prediction based on the contagion model. Actual impact depends on the full interaction graph." if direction == "negative" else None,
    }


# ─── Agent Classification ───

KNOWN_DEFI_PROTOCOLS = {
    "0x2626664c2603336e57b271c5c0b26f421741e481",  # Uniswap V3
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # Uniswap Universal
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",  # USDbC
    "0x4200000000000000000000000000000000000006",  # WETH
}

KNOWN_BRIDGE_CONTRACTS = {
    "0x4200000000000000000000000000000000000010",  # L2StandardBridge
    "0x49048044d57e1c92a77f79988d21fa8faf74e97e",  # Base Portal
}

KNOWN_ERC8004 = {
    "0x8004a169fb4a3325136eb29fa0ceb6d2e539a432",  # Identity
    "0x8004baa17c55a88189ae136b182e5fda19de9b63",  # Reputation
}


def _classify_agent(score_dict: dict, edges: list) -> dict:
    """Classify an agent's behavior based on on-chain patterns."""
    labels = []
    counterparty_addrs = {e["counterparty"].lower() for e in edges}

    # DeFi activity
    defi_overlap = counterparty_addrs & KNOWN_DEFI_PROTOCOLS
    if defi_overlap:
        labels.append("defi_user")

    # Bridge usage
    bridge_overlap = counterparty_addrs & KNOWN_BRIDGE_CONTRACTS
    if bridge_overlap:
        labels.append("bridge_user")

    # ERC-8004 ecosystem participant
    erc8004_overlap = counterparty_addrs & KNOWN_ERC8004
    if erc8004_overlap:
        labels.append("erc8004_native")

    # Activity patterns
    act = score_dict.get("activity", 0)
    lon = score_dict.get("longevity", 0)
    total_edges = len(edges)

    if act <= 10 and lon >= 30:
        labels.append("dormant")
    elif act >= 70 and total_edges >= 20:
        labels.append("power_user")
    elif act >= 60 and total_edges < 5:
        labels.append("narrow_focus")

    # Bot signals
    if score_dict.get("sybil_flagged"):
        labels.append("sybil_suspect")
    contagion = score_dict.get("contagion_adjustment", 0)
    if contagion and contagion <= -10:
        labels.append("toxic_neighborhood")

    # High-value participant
    if score_dict.get("trust_score", 0) >= 75 and score_dict.get("agent_identity", 0) >= 70:
        labels.append("high_trust_verified")

    if not labels:
        labels.append("unclassified")

    # Primary category
    if "sybil_suspect" in labels:
        primary = "sybil_suspect"
    elif "high_trust_verified" in labels:
        primary = "high_trust_verified"
    elif "defi_user" in labels:
        primary = "defi_user"
    elif "bridge_user" in labels:
        primary = "bridge_user"
    elif "dormant" in labels:
        primary = "dormant"
    else:
        primary = labels[0]

    return {"primary": primary, "labels": labels, "interactions_analyzed": total_edges}


@app.get("/api/classify/{agent_id}", tags=["Classification"])
async def classify_agent(agent_id: int):
    """Classify an agent's behavior based on on-chain interaction patterns."""
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"Agent {agent_id} not scored yet")
    edges = await db.get_edges(agent_id)
    classification = _classify_agent(score, edges)
    return {
        "agent_id": agent_id,
        "classification": classification,
        "score": score["trust_score"],
        "verdict": score["verdict"],
    }


# ─── Webhooks ───


def _is_private_url(url: str) -> bool:
    """Block webhooks to private/internal IPs."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", ""):
            return True
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return True
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            pass  # hostname, not IP — allow DNS names
    except Exception:
        return True
    return False


VALID_WEBHOOK_EVENTS = ["score_update", "verdict_changed", "sybil_detected", "trust_degraded"]
MAX_WEBHOOKS = 50


@app.post("/api/webhooks", tags=["Webhooks"])
async def register_webhook(request: Request):
    """Register a webhook URL to receive trust alerts.
    Body: {"url": "https://...", "events": [...], "secret": "optional_signing_secret"}
    If events is omitted, all events are subscribed.
    Webhooks are scoped to your API key — you can only list/delete your own."""
    body = await request.json()
    url = body.get("url", "")
    if not url or not url.startswith("http"):
        raise HTTPException(400, "Provide a valid webhook URL")
    if _is_private_url(url):
        raise HTTPException(400, "Webhook URL must not point to private/internal addresses")
    count = await db.count_webhooks()
    if count >= MAX_WEBHOOKS:
        raise HTTPException(429, "Maximum 50 webhooks allowed")
    events = body.get("events", VALID_WEBHOOK_EVENTS[:])
    for e in events:
        if e not in VALID_WEBHOOK_EVENTS:
            raise HTTPException(400, f"Invalid event '{e}'. Valid: {VALID_WEBHOOK_EVENTS}")
    wh_secret = body.get("secret", "")
    owner_key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    wh_id = f"wh_{secrets.token_hex(8)}"
    await db.save_webhook(wh_id, url, events, owner_key=owner_key, secret=wh_secret)
    return {"webhook_id": wh_id, "url": url, "events": events, "status": "registered"}


@app.get("/api/webhooks", tags=["Webhooks"])
async def list_webhooks(request: Request):
    """List webhooks owned by the caller's API key."""
    owner_key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    webhooks = await db.get_webhooks(owner_key=owner_key)
    return {"webhooks": webhooks, "total": len(webhooks)}


@app.delete("/api/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_webhook(webhook_id: str, request: Request):
    """Remove a webhook. Only the owner (by API key) can delete it."""
    owner_key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    deleted = await db.delete_webhook(webhook_id, owner_key=owner_key)
    if not deleted:
        raise HTTPException(404, f"Webhook {webhook_id} not found or not owned by you")
    return {"status": "deleted", "webhook_id": webhook_id}


async def _deliver_webhook(url: str, payload: dict, wh_secret: str = "", max_retries: int = 3):
    """Deliver a single webhook with HMAC signature and retry + exponential backoff."""
    payload_bytes = json_module.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if wh_secret:
        signature = "sha256=" + hmac.new(
            wh_secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()
        headers["X-SentinelNet-Signature"] = signature
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=payload_bytes, headers=headers)
                if resp.status_code < 400:
                    return True
                if resp.status_code < 500:
                    logger.warning(f"Webhook {url} returned {resp.status_code}, not retrying")
                    return False
        except Exception as exc:
            logger.debug(f"Webhook {url} attempt {attempt + 1} failed: {exc}")
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff
    logger.warning(f"Webhook {url} failed after {max_retries} attempts")
    return False


async def _fire_webhooks(event: str, payload: dict):
    """Fire webhooks for matching events. Detects derived events from payload context."""
    webhooks = await db.get_webhooks_with_secrets()
    if not webhooks:
        return

    # Determine which events this payload triggers
    triggered_events = {event}

    prev_score = payload.get("previous_score")
    new_score = payload.get("trust_score")
    prev_verdict = payload.get("previous_verdict")
    new_verdict = payload.get("verdict")
    sybil = payload.get("sybil_flagged", False)

    if prev_verdict and new_verdict and prev_verdict != new_verdict:
        triggered_events.add("verdict_changed")
    if prev_score is not None and new_score is not None and new_score < prev_score:
        triggered_events.add("trust_degraded")
    if sybil:
        triggered_events.add("sybil_detected")

    delivery_payload = {
        "event": event,
        "triggered_events": list(triggered_events),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    tasks = []
    for wh in webhooks:
        subscribed = set(wh["events"])
        if triggered_events & subscribed:
            tasks.append(_deliver_webhook(wh["url"], delivery_payload, wh_secret=wh.get("secret", "")))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ─── Admin ───

# Agent reference set by main.py at startup
_agent_ref = None


def _require_admin(request: Request):
    """Verify the request carries a valid admin key."""
    admin_key = _settings.ADMIN_KEY.strip()
    if not admin_key:
        raise HTTPException(503, "Admin endpoint not configured")
    provided = request.headers.get("x-admin-key", "") or request.query_params.get("admin_key", "")
    if not provided or not hmac.compare_digest(provided, admin_key):
        raise HTTPException(403, "Invalid or missing admin key")


@app.post("/api/score/{agent_id}", tags=["Admin"])
async def trigger_score(agent_id: int, request: Request):
    """Trigger on-demand scoring for a specific agent. Requires admin key (X-Admin-Key header)."""
    _require_admin(request)
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
    except Exception:
        raise HTTPException(500, "Scoring failed")


# ─── WebSocket Live Feed ───

class ConnectionManager:
    """Manages WebSocket connections for live score updates."""
    def __init__(self, max_connections: int = 100):
        self.active: List[WebSocket] = []
        self.max_connections = max_connections

    async def connect(self, ws: WebSocket):
        if len(self.active) >= self.max_connections:
            await ws.close(code=1013, reason="Too many connections")
            return False
        await ws.accept()
        self.active.append(ws)
        return True

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()
_last_broadcast_time: str | None = None
_broadcast_count: int = 0


@app.get("/ws/scores", tags=["WebSocket"])
async def ws_scores_info():
    """Informational response when /ws/scores is accessed over plain HTTP."""
    return {
        "error": "WebSocket endpoint",
        "usage": "Connect via ws:// or wss:// protocol",
        "example": "wss://sentinelnet.gudman.xyz/ws/scores",
    }


@app.websocket("/ws/scores")
async def ws_scores(websocket: WebSocket):
    """WebSocket endpoint streaming real-time score updates."""
    if not await ws_manager.connect(websocket):
        return
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def broadcast_score_update(agent_id: int, score: int, verdict: str, wallet: str):
    """Called by the agent after scoring -- broadcasts to all connected WebSocket clients."""
    global _last_broadcast_time, _broadcast_count
    _last_broadcast_time = datetime.now(timezone.utc).isoformat()
    _broadcast_count += 1
    await ws_manager.broadcast({
        "event": "score_update",
        "agent_id": agent_id,
        "trust_score": score,
        "verdict": verdict,
        "wallet": wallet[:10] + "..." if wallet else "",
        "timestamp": _last_broadcast_time,
        "connections": len(ws_manager.active),
    })


@app.get("/api/ws-stats", tags=["WebSocket"])
async def ws_stats():
    """Return WebSocket connection count, last broadcast time, and broadcast count."""
    return {
        "active_connections": len(ws_manager.active),
        "max_connections": ws_manager.max_connections,
        "last_broadcast_time": _last_broadcast_time,
        "total_broadcasts": _broadcast_count,
        "rescore_interval_seconds": RESCORE_INTERVAL_SECONDS,
        "rescore_batch_size": RESCORE_BATCH_SIZE,
    }


# ─── Rate Limiting ───

_rate_limits: dict = defaultdict(list)  # ip -> [timestamps]
_request_counter: int = 0  # total API requests served
RATE_LIMIT_FREE = 100       # requests per hour (unauthenticated)
RATE_LIMIT_AUTH = 1000       # requests per hour (with API key)


def _check_rate_limit(ip: str, api_key: str = None) -> tuple:
    """Returns (allowed: bool, limit: int, remaining: int, reset: int)."""
    now = time.time()
    cutoff = now - 3600
    limit = RATE_LIMIT_AUTH if (api_key and _is_valid_api_key(api_key)) else RATE_LIMIT_FREE
    # Clean old entries
    _rate_limits[ip] = sorted(t for t in _rate_limits[ip] if t > cutoff)
    remaining = max(0, limit - len(_rate_limits[ip]))
    # Reset = when the oldest request in the window expires (frees a slot)
    if _rate_limits[ip]:
        reset = int(_rate_limits[ip][0] + 3600)
    else:
        reset = int(now + 3600)
    if remaining <= 0:
        return False, limit, 0, reset
    _rate_limits[ip].append(now)
    return True, limit, remaining - 1, reset


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    global _request_counter
    _request_counter += 1

    # Skip rate limiting for pages, static assets, metrics, and WebSocket
    path = request.url.path
    if path.startswith("/_next") or path.startswith("/ws") or path in ("/", "/dashboard", "/graph", "/leaderboard", "/marketplace", "/docs-guide", "/metrics"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    api_key = request.headers.get("x-api-key", "")
    allowed, limit, remaining, reset = _check_rate_limit(ip, api_key)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "limit": limit, "reset": reset},
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
                "Retry-After": str(reset - int(time.time())),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
    return response


_key_registrations: dict = defaultdict(list)  # ip -> [timestamps]
MAX_KEY_REGISTRATIONS = 3  # per IP per hour


@app.post("/api/keys", tags=["Auth"])
async def register_api_key(request: Request):
    """Register for an API key. Grants authenticated API access and higher
    rate limits (1000 req/hr). The key is stored in memory and valid for the
    lifetime of the server process. Limited to 3 registrations per IP per hour.

    Body: {"email": "dev@example.com"}
    Returns: {"api_key": "sk-sn-...", "rate_limit": 1000, "note": "..."}
    """
    # Rate-limit key registrations per IP
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - 3600
    _key_registrations[ip] = [t for t in _key_registrations[ip] if t > cutoff]
    if len(_key_registrations[ip]) >= MAX_KEY_REGISTRATIONS:
        raise HTTPException(429, "Too many key registrations. Try again later.")
    _key_registrations[ip].append(now)

    body = await request.json()
    email = body.get("email", "")
    if not email or "@" not in email:
        raise HTTPException(400, "Provide a valid email")
    key = "sk-sn-" + secrets.token_hex(24)
    _api_keys[key] = {"email": email, "created_at": datetime.now(timezone.utc).isoformat()}
    return {"api_key": key, "rate_limit": RATE_LIMIT_AUTH, "note": "Include as X-API-Key header"}


# ─── Prometheus Metrics ───

@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics():
    """Prometheus-format metrics endpoint."""
    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]

    total = len(scores)
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1

    trust_scores = [s["trust_score"] for s in scores]
    avg_score = round(sum(trust_scores) / total, 2) if total else 0
    sybil_count = sum(1 for s in scores if s.get("sybil_flagged"))

    # Ecosystem health: same formula as /api/stats
    trust_pct = (verdicts["TRUST"] / total) if total else 0
    sybil_pct = (sybil_count / total) if total else 0
    ecosystem_health = round(avg_score * 0.4 + trust_pct * 100 * 0.3 + (1 - sybil_pct) * 100 * 0.3) if total else 0

    # Total threats from DB
    cursor = await db.conn.execute("SELECT COUNT(*) FROM threats")
    row = await cursor.fetchone()
    threats_total = row[0] if row else 0

    ws_connections = len(ws_manager.active)

    lines = [
        "# HELP sentinelnet_agents_scored_total Total number of agents scored",
        "# TYPE sentinelnet_agents_scored_total gauge",
        f"sentinelnet_agents_scored_total {total}",
        "",
        "# HELP sentinelnet_agents_trusted Number of agents with TRUST verdict",
        "# TYPE sentinelnet_agents_trusted gauge",
        f"sentinelnet_agents_trusted {verdicts['TRUST']}",
        "",
        "# HELP sentinelnet_agents_caution Number of agents with CAUTION verdict",
        "# TYPE sentinelnet_agents_caution gauge",
        f"sentinelnet_agents_caution {verdicts['CAUTION']}",
        "",
        "# HELP sentinelnet_agents_rejected Number of agents with REJECT verdict",
        "# TYPE sentinelnet_agents_rejected gauge",
        f"sentinelnet_agents_rejected {verdicts['REJECT']}",
        "",
        "# HELP sentinelnet_sybil_flagged Number of sybil-flagged agents",
        "# TYPE sentinelnet_sybil_flagged gauge",
        f"sentinelnet_sybil_flagged {sybil_count}",
        "",
        "# HELP sentinelnet_threats_total Total threats logged",
        "# TYPE sentinelnet_threats_total gauge",
        f"sentinelnet_threats_total {threats_total}",
        "",
        "# HELP sentinelnet_avg_trust_score Average trust score across all agents",
        "# TYPE sentinelnet_avg_trust_score gauge",
        f"sentinelnet_avg_trust_score {avg_score}",
        "",
        "# HELP sentinelnet_ecosystem_health Ecosystem health score (0-100)",
        "# TYPE sentinelnet_ecosystem_health gauge",
        f"sentinelnet_ecosystem_health {ecosystem_health}",
        "",
        "# HELP sentinelnet_websocket_connections Current WebSocket connections",
        "# TYPE sentinelnet_websocket_connections gauge",
        f"sentinelnet_websocket_connections {ws_connections}",
        "",
        "# HELP sentinelnet_api_requests_total Total API requests served",
        "# TYPE sentinelnet_api_requests_total counter",
        f"sentinelnet_api_requests_total {_request_counter}",
    ]

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4",
    )


# ─── Anomaly Detection ───

def _detect_anomalies(scores: list, history_map: dict, wallet_agent_map: dict,
                      recent_threats: list) -> list:
    """Pure detection logic — returns list of anomaly dicts.

    Args:
        scores: list of score dicts (already decay-applied)
        history_map: {agent_id: [history rows newest-first]}
        wallet_agent_map: {wallet: [agent_ids]}
        recent_threats: threat rows from last 24h
    """
    anomalies = []

    # Pre-compute stats for outlier detection
    trust_values = [s["trust_score"] for s in scores]
    if len(trust_values) >= 2:
        mean_score = sum(trust_values) / len(trust_values)
        variance = sum((t - mean_score) ** 2 for t in trust_values) / len(trust_values)
        std_dev = variance ** 0.5
    else:
        mean_score = trust_values[0] if trust_values else 0
        std_dev = 0

    for s in scores:
        agent_id = s["agent_id"]
        trust = s["trust_score"]

        # 1) Rapid score drops (>15 pts between consecutive scorings)
        history = history_map.get(agent_id, [])
        if len(history) >= 2:
            prev = history[1]["trust_score"]
            curr = history[0]["trust_score"]
            drop = prev - curr
            if drop >= 15:
                anomalies.append({
                    "type": "rapid_drop",
                    "severity": "HIGH" if drop >= 25 else "MEDIUM",
                    "agent_id": agent_id,
                    "detail": f"Score dropped {drop} points ({prev} -> {curr}) in recent scoring",
                    "previous_score": prev,
                    "current_score": curr,
                })

        # 2) Suspicious perfect scores — score=100 but low activity or low longevity
        if trust == 100:
            activity = s.get("activity", 0)
            longevity = s.get("longevity", 0)
            if activity < 30 or longevity < 30:
                anomalies.append({
                    "type": "suspicious_perfect_score",
                    "severity": "HIGH",
                    "agent_id": agent_id,
                    "detail": f"Perfect score (100) with low activity ({activity}) or low longevity ({longevity})",
                })

        # 3) Suspicious high score (low longevity, high trust) — keep existing check
        if s.get("longevity", 0) < 20 and trust >= 70:
            anomalies.append({
                "type": "suspicious_high_score",
                "severity": "MEDIUM",
                "agent_id": agent_id,
                "detail": f"New wallet (longevity={s['longevity']}) with unusually high score ({trust})",
            })

        # 4) Score outliers — deviation > 2 standard deviations from mean
        if std_dev > 0 and len(trust_values) >= 5:
            deviation = abs(trust - mean_score)
            if deviation > 2 * std_dev:
                direction = "above" if trust > mean_score else "below"
                anomalies.append({
                    "type": "score_outlier",
                    "severity": "MEDIUM" if deviation <= 3 * std_dev else "HIGH",
                    "agent_id": agent_id,
                    "detail": f"Score {trust} is {deviation:.1f} points {direction} mean ({mean_score:.1f}, std={std_dev:.1f})",
                })

        # 5) Heavy contagion — toxic neighborhood
        contagion = s.get("contagion_adjustment", 0)
        if contagion <= -10:
            anomalies.append({
                "type": "toxic_neighborhood",
                "severity": "HIGH",
                "agent_id": agent_id,
                "detail": f"Score reduced by {abs(contagion)} from interactions with low-trust agents",
            })

    # 6) Sudden sybil clusters — wallets controlling 3+ agents
    for wallet, agent_ids in wallet_agent_map.items():
        if len(agent_ids) >= 3:
            anomalies.append({
                "type": "sybil_cluster",
                "severity": "HIGH",
                "agent_id": agent_ids[0],
                "affected_agents": sorted(agent_ids),
                "detail": f"Wallet {wallet[:10]}... controls {len(agent_ids)} agents: {sorted(agent_ids)}",
            })

    # 7) Recent sybil threats from threat feed (last 24h)
    for t in recent_threats:
        if t.get("threat_type") == "SYBIL_CLUSTER":
            anomalies.append({
                "type": "sybil_cluster_detected",
                "severity": "HIGH",
                "agent_id": t.get("agent_id"),
                "detail": t.get("details", "Sybil cluster detected in last 24 hours"),
            })

    # Sort: HIGH first, then MEDIUM, then LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    anomalies.sort(key=lambda x: severity_order.get(x["severity"], 3))
    return anomalies


async def _compute_anomalies_cached() -> tuple:
    """Return (anomalies_list, checked_count) using a TTL cache.

    The full anomaly computation is expensive (N+1 history queries for every
    scored agent).  Cache the result for _ANOMALY_CACHE_TTL seconds so that
    repeated requests (pagination, different severity filters) don't recompute.
    """
    now = time.monotonic()
    if (
        _anomaly_cache["anomalies"] is not None
        and (now - _anomaly_cache["ts"]) < _ANOMALY_CACHE_TTL
    ):
        return _anomaly_cache["anomalies"], _anomaly_cache["checked"]

    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]

    # Build history map (batch fetch avoids N+1)
    history_map = {}
    for s in scores:
        aid = s["agent_id"]
        history_map[aid] = await db.get_score_history(aid, limit=5)

    # Wallet-agent map for sybil cluster detection
    wallet_agent_map = await db.get_wallet_agent_map()

    # Recent threats (last 24h) for sybil cluster feed
    all_threats = await db.get_threats(limit=200)
    utcnow = datetime.now(timezone.utc)
    recent_threats = []
    for t in all_threats:
        try:
            created = datetime.fromisoformat(t["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if (utcnow - created).total_seconds() <= 86400:
                recent_threats.append(t)
        except (ValueError, KeyError):
            pass

    anomalies = _detect_anomalies(scores, history_map, wallet_agent_map, recent_threats)

    _anomaly_cache["anomalies"] = anomalies
    _anomaly_cache["checked"] = len(scores)
    _anomaly_cache["ts"] = now
    return anomalies, len(scores)


@app.get("/api/anomalies", tags=["Threats"])
async def get_anomalies(
    limit: int = Query(50, ge=1, le=500, description="Max anomalies to return"),
    offset: int = Query(0, ge=0, description="Number of anomalies to skip"),
    severity: str = Query(None, description="Filter by severity: HIGH, MEDIUM, or LOW"),
):
    """Detect and return current anomalies in the trust scoring system.

    Detects: rapid score drops, suspicious perfect scores, sybil clusters,
    score outliers, and toxic neighborhoods.

    Supports pagination via `limit` (default 50) and `offset` (default 0)."""
    all_anomalies, checked = await _compute_anomalies_cached()

    # Filter by severity if requested
    if severity:
        sev_upper = severity.upper()
        filtered = [a for a in all_anomalies if a["severity"] == sev_upper]
    else:
        filtered = all_anomalies

    total = len(filtered)

    # Apply offset + limit pagination
    page = filtered[offset:offset + limit]

    return {
        "anomalies": page,
        "total": total,
        "returned": len(page),
        "limit": limit,
        "offset": offset,
        "checked": checked,
    }


# ─── Prometheus Metrics ───

_metrics = {
    "agents_scored_total": 0,
    "verdicts": {"TRUST": 0, "CAUTION": 0, "REJECT": 0},
    "api_requests_total": 0,
    "sybil_detections_total": 0,
    "ws_connections_active": 0,
}


@app.get("/metrics", tags=["System"], response_class=Response)
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    scores = await db.get_all_scores()
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    sybil_count = sum(1 for s in scores if s.get("sybil_flagged"))

    lines = [
        "# HELP sentinelnet_agents_scored_total Total number of agents scored",
        "# TYPE sentinelnet_agents_scored_total gauge",
        f"sentinelnet_agents_scored_total {len(scores)}",
        "# HELP sentinelnet_verdicts_total Verdict distribution",
        "# TYPE sentinelnet_verdicts_total gauge",
        f'sentinelnet_verdicts_total{{verdict="TRUST"}} {verdicts["TRUST"]}',
        f'sentinelnet_verdicts_total{{verdict="CAUTION"}} {verdicts["CAUTION"]}',
        f'sentinelnet_verdicts_total{{verdict="REJECT"}} {verdicts["REJECT"]}',
        "# HELP sentinelnet_sybil_detections_total Number of agents flagged as sybil",
        "# TYPE sentinelnet_sybil_detections_total gauge",
        f"sentinelnet_sybil_detections_total {sybil_count}",
        "# HELP sentinelnet_websocket_connections_active Active WebSocket connections",
        "# TYPE sentinelnet_websocket_connections_active gauge",
        f"sentinelnet_websocket_connections_active {len(ws_manager.active)}",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


# ─── Marketplace ───

@app.get("/marketplace", response_class=HTMLResponse, include_in_schema=False)
async def marketplace_page():
    return FileResponse("dashboard/marketplace.html")


@app.get("/api/marketplace", tags=["Marketplace"])
async def marketplace_list(
    verdict: str = Query(None, description="Filter by verdict: TRUST, CAUTION, REJECT"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum trust score"),
    sort: str = Query("score", description="Sort by: score, newest"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    search: str = Query(None, description="Search by agent ID or wallet prefix"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Browse scored agents for the marketplace with filtering, sorting, and pagination."""
    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]

    # Filters
    if verdict:
        scores = [s for s in scores if s.get("verdict", "").upper() == verdict.upper()]
    if min_score > 0:
        scores = [s for s in scores if s.get("trust_score", 0) >= min_score]
    if search:
        search_lower = search.lower()
        scores = [s for s in scores if search_lower in str(s["agent_id"]) or search_lower in s.get("wallet", "").lower()]

    # Sort
    descending = order.lower() != "asc"
    if sort == "score":
        scores.sort(key=lambda s: s.get("trust_score", 0), reverse=descending)
    elif sort in ("newest", "recent"):
        scores.sort(key=lambda s: s.get("scored_at", ""), reverse=descending)

    total = len(scores)
    start = (page - 1) * per_page
    agents = scores[start:start + per_page]

    # Enrich with classification labels
    for a in agents:
        edges = await db.get_edges(a["agent_id"])
        a["classification"] = _classify_agent(a, edges)
        a["explanation"] = _explain_score(a)

    return {
        "agents": agents,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total else 0,
    }
