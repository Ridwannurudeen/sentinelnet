import asyncio
import math
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from web3 import Web3
from db import Database
from config import Settings
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
                             "action": "Very low on-chain activity. Execute regular transactions on Base — interact with verified protocols like Uniswap, USDC, or WETH."})
            else:
                recs.append({"dimension": "activity", "score": val, "priority": "medium",
                             "action": "Increase transaction frequency and maintain an ETH balance on Base. Active 60%+ of days maximizes this dimension."})
        elif name == "counterparty" and val < 70:
            if val < 30:
                recs.append({"dimension": "counterparty", "score": val, "priority": "high",
                             "action": "Interact with verified protocols (Uniswap, USDC, WETH). Avoid transactions with flagged or unknown addresses."})
            else:
                recs.append({"dimension": "counterparty", "score": val, "priority": "medium",
                             "action": "Diversify interactions — engage with 30+ unique verified counterparties to maximize diversity bonus."})
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


@asynccontextmanager
async def lifespan(app):
    await db.init()
    yield
    await db.close()


app = FastAPI(
    title="SentinelNet",
    version="2.2.0",
    description="Autonomous reputation immune system for ERC-8004 agents on Base. "
                "5-dimensional trust scoring with trust contagion, sybil detection, "
                "threat intelligence, IPFS evidence, and EAS attestations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


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


@app.get("/graph", response_class=HTMLResponse, include_in_schema=False)
async def graph_page():
    return FileResponse("dashboard/graph.html")


@app.get("/leaderboard", response_class=HTMLResponse, include_in_schema=False)
async def leaderboard_page():
    return FileResponse("dashboard/leaderboard.html")


# ─── API ───

@app.get("/api/health", tags=["System"])
async def health():
    """Health check endpoint. Returns service status and version."""
    return {"status": "ok", "service": "sentinelnet", "version": "2.2.0"}


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
    try:
        agent_ids = [int(x.strip()) for x in agents.split(",")]
    except ValueError:
        raise HTTPException(400, "Provide comma-separated integer agent IDs")
    if len(agent_ids) > 10:
        raise HTTPException(400, "Maximum 10 agents for comparison")

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


# ─── Evidence ───

@app.get("/evidence/{agent_id}", tags=["Evidence"])
async def get_evidence(agent_id: int):
    """Verifiable evidence JSON for an agent's trust score.
    Content-addressed: the hash in the query string can be verified against the response."""
    score = await db.get_score(agent_id)
    if not score:
        raise HTTPException(404, f"No evidence for agent {agent_id}")
    return {
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

_settings = Settings()
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
    except Exception as e:
        raise HTTPException(500, f"On-chain read failed: {str(e)}")


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

# In-memory webhook store (persists until restart — lightweight for hackathon)
_webhooks = {}  # id -> {url, events, created_at}
_webhook_counter = 0


@app.post("/api/webhooks", tags=["Webhooks"])
async def register_webhook(request: Request):
    """Register a webhook URL to receive trust alerts.
    Body: {"url": "https://...", "events": ["trust_degraded", "sybil_detected", "verdict_changed"]}
    If events is omitted, all events are subscribed."""
    global _webhook_counter
    body = await request.json()
    url = body.get("url", "")
    if not url or not url.startswith("http"):
        raise HTTPException(400, "Provide a valid webhook URL")
    events = body.get("events", ["trust_degraded", "sybil_detected", "verdict_changed"])
    _webhook_counter += 1
    wh_id = f"wh_{_webhook_counter}"
    _webhooks[wh_id] = {
        "url": url,
        "events": events,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"webhook_id": wh_id, "url": url, "events": events, "status": "registered"}


@app.get("/api/webhooks", tags=["Webhooks"])
async def list_webhooks():
    """List all registered webhooks."""
    return {"webhooks": [{"id": k, **v} for k, v in _webhooks.items()], "total": len(_webhooks)}


@app.delete("/api/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_webhook(webhook_id: str):
    """Remove a registered webhook."""
    if webhook_id not in _webhooks:
        raise HTTPException(404, f"Webhook {webhook_id} not found")
    del _webhooks[webhook_id]
    return {"status": "deleted", "webhook_id": webhook_id}


async def _fire_webhooks(event: str, payload: dict):
    """Fire webhooks for a given event (called internally by the agent)."""
    import httpx
    for wh_id, wh in _webhooks.items():
        if event in wh["events"]:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(wh["url"], json={
                        "event": event,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        **payload,
                    })
            except Exception:
                pass  # Fire and forget


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


# ─── WebSocket Live Feed ───

class ConnectionManager:
    """Manages WebSocket connections for live score updates."""
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

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


@app.websocket("/ws/scores")
async def ws_scores(websocket: WebSocket):
    """WebSocket endpoint streaming real-time score updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def broadcast_score_update(agent_id: int, score: int, verdict: str, wallet: str):
    """Called by the agent after scoring — broadcasts to all connected WebSocket clients."""
    await ws_manager.broadcast({
        "event": "score_update",
        "agent_id": agent_id,
        "trust_score": score,
        "verdict": verdict,
        "wallet": wallet[:10] + "..." if wallet else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connections": len(ws_manager.active),
    })


# ─── Rate Limiting ───

_rate_limits: dict = defaultdict(list)  # ip -> [timestamps]
RATE_LIMIT_FREE = 100       # requests per hour (unauthenticated)
RATE_LIMIT_AUTH = 1000       # requests per hour (with API key)
_api_keys: dict = {}         # key -> {email, created_at}
_api_key_counter = 0


def _check_rate_limit(ip: str, api_key: str = None) -> tuple:
    """Returns (allowed: bool, limit: int, remaining: int, reset: int)."""
    now = time.time()
    cutoff = now - 3600
    limit = RATE_LIMIT_AUTH if (api_key and api_key in _api_keys) else RATE_LIMIT_FREE
    # Clean old entries
    _rate_limits[ip] = [t for t in _rate_limits[ip] if t > cutoff]
    remaining = max(0, limit - len(_rate_limits[ip]))
    reset = int(cutoff + 3600)
    if remaining <= 0:
        return False, limit, 0, reset
    _rate_limits[ip].append(now)
    return True, limit, remaining - 1, reset


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for pages, static assets, and WebSocket
    path = request.url.path
    if path.startswith("/_next") or path.startswith("/ws") or not path.startswith("/api"):
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


@app.post("/api/keys", tags=["Auth"])
async def register_api_key(request: Request):
    """Register for an API key to get higher rate limits (1000 req/hr).
    Body: {"email": "dev@example.com"}"""
    global _api_key_counter
    body = await request.json()
    email = body.get("email", "")
    if not email or "@" not in email:
        raise HTTPException(400, "Provide a valid email")
    import hashlib
    _api_key_counter += 1
    raw = f"sentinelnet-{email}-{_api_key_counter}-{time.time()}"
    key = "sk-sn-" + hashlib.sha256(raw.encode()).hexdigest()[:32]
    _api_keys[key] = {"email": email, "created_at": datetime.now(timezone.utc).isoformat()}
    return {"api_key": key, "rate_limit": RATE_LIMIT_AUTH, "note": "Include as X-API-Key header"}


# ─── Anomaly Detection ───

@app.get("/api/anomalies", tags=["Threats"])
async def get_anomalies():
    """Detect and return current anomalies: rapid score drops, suspicious spikes,
    and potential gaming behavior."""
    scores = await db.get_all_scores()
    scores = [_apply_decay(s) for s in scores]
    anomalies = []

    for s in scores:
        agent_id = s["agent_id"]
        trust = s["trust_score"]
        raw = s.get("trust_score_raw", trust)

        # Check history for rapid drops
        history = await db.get_score_history(agent_id, limit=5)
        if len(history) >= 2:
            prev = history[1]["trust_score"]
            curr = history[0]["trust_score"]
            drop = prev - curr
            if drop >= 15:
                anomalies.append({
                    "type": "rapid_drop",
                    "severity": "high" if drop >= 25 else "medium",
                    "agent_id": agent_id,
                    "detail": f"Score dropped {drop} points ({prev} → {curr}) in recent scoring",
                    "previous_score": prev,
                    "current_score": curr,
                })

        # Suspicious: very new but very high score
        if s.get("longevity", 0) < 20 and trust >= 70:
            anomalies.append({
                "type": "suspicious_high_score",
                "severity": "medium",
                "agent_id": agent_id,
                "detail": f"New wallet (longevity={s['longevity']}) with unusually high score ({trust})",
            })

        # Heavy contagion
        contagion = s.get("contagion_adjustment", 0)
        if contagion <= -10:
            anomalies.append({
                "type": "toxic_neighborhood",
                "severity": "high",
                "agent_id": agent_id,
                "detail": f"Score reduced by {abs(contagion)} from interactions with low-trust agents",
            })

    anomalies.sort(key=lambda x: 0 if x["severity"] == "high" else 1)
    return {"anomalies": anomalies, "total": len(anomalies), "checked": len(scores)}


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
    sort: str = Query("score", description="Sort by: score, recent"),
    search: str = Query(None, description="Search by agent ID or wallet"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Browse scored agents for the marketplace with filtering and pagination."""
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
    if sort == "score":
        scores.sort(key=lambda s: s.get("trust_score", 0), reverse=True)
    elif sort == "recent":
        scores.sort(key=lambda s: s.get("scored_at", ""), reverse=True)

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
