import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from db import Database

app = Server("sentinelnet")
db = Database()
_agent_ref = None  # Set by main.py to enable fresh analysis


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="check_trust",
            description="Check the trust score of an ERC-8004 registered agent on Base.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "integer",
                        "description": "ERC-8004 agent ID (uint256)",
                    },
                    "fresh": {
                        "type": "boolean",
                        "description": "If true, runs fresh on-chain analysis instead of returning cached score.",
                        "default": False,
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="list_scored_agents",
            description="List all agents scored by SentinelNet with trust verdicts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "verdict": {
                        "type": "string",
                        "description": "Filter by verdict: TRUST, CAUTION, or REJECT",
                        "enum": ["TRUST", "CAUTION", "REJECT"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max agents to return (default 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_ecosystem_stats",
            description="Get aggregate trust statistics for the ERC-8004 agent ecosystem on Base.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_score_history",
            description="Get the scoring history for an agent to see trust trends over time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "integer",
                        "description": "ERC-8004 agent ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max history entries (default 20)",
                        "default": 20,
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="get_threat_feed",
            description="Get real-time threat intelligence feed: sybil clusters, trust degradations, contagion events. "
                        "Use this to protect your agent from interacting with compromised or malicious agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max threat events to return (default 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if not db.conn:
        await db.init()

    if name == "check_trust":
        return await _handle_check_trust(arguments)
    elif name == "list_scored_agents":
        return await _handle_list_agents(arguments)
    elif name == "get_ecosystem_stats":
        return await _handle_stats(arguments)
    elif name == "get_score_history":
        return await _handle_history(arguments)
    elif name == "get_threat_feed":
        return await _handle_threats(arguments)
    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def _handle_check_trust(args):
    agent_id = args["agent_id"]
    fresh = args.get("fresh", False)

    if fresh and _agent_ref:
        try:
            result = await _agent_ref.analyze_agent(agent_id)
            if result:
                score = await db.get_score(agent_id)
                if score:
                    return [TextContent(type="text", text=json.dumps(score, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Fresh analysis failed: {str(e)}",
                "agent_id": agent_id,
            }))]

    score = await db.get_score(agent_id)
    if not score:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Agent {agent_id} not scored yet. Use fresh=true to trigger analysis.",
            "agent_id": agent_id,
        }))]
    return [TextContent(type="text", text=json.dumps(score, default=str))]


async def _handle_list_agents(args):
    verdict_filter = args.get("verdict")
    limit = args.get("limit", 50)
    scores = await db.get_all_scores()
    if verdict_filter:
        scores = [s for s in scores if s.get("verdict", "").upper() == verdict_filter.upper()]
    scores = scores[:limit]
    return [TextContent(type="text", text=json.dumps({
        "agents": [{
            "agent_id": s["agent_id"],
            "trust_score": s["trust_score"],
            "verdict": s["verdict"],
            "wallet": s["wallet"],
        } for s in scores],
        "count": len(scores),
    }, default=str))]


async def _handle_stats(args):
    scores = await db.get_all_scores()
    verdicts = {"TRUST": 0, "CAUTION": 0, "REJECT": 0}
    for s in scores:
        v = s.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1
    trust_scores = [s["trust_score"] for s in scores]
    return [TextContent(type="text", text=json.dumps({
        "agents_scored": len(scores),
        "avg_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
        "verdicts": verdicts,
        "sybil_flagged": sum(1 for s in scores if s.get("sybil_flagged")),
    }))]


async def _handle_history(args):
    agent_id = args["agent_id"]
    limit = args.get("limit", 20)
    history = await db.get_score_history(agent_id, limit=limit)
    if not history:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No history for agent {agent_id}",
            "agent_id": agent_id,
        }))]
    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "history": history,
        "entries": len(history),
    }, default=str))]


async def _handle_threats(args):
    limit = args.get("limit", 20)
    threats = await db.get_threats(limit=limit)
    return [TextContent(type="text", text=json.dumps({
        "threats": threats,
        "count": len(threats),
    }, default=str))]


async def main():
    await db.init()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
