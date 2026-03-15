import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from db import Database

app = Server("sentinelnet")
db = Database()


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="check_trust",
            description="Check the trust score of an ERC-8004 registered agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "integer",
                        "description": "ERC-8004 agent ID (uint256)",
                    },
                    "fresh": {
                        "type": "boolean",
                        "description": "If true, runs fresh analysis. Default false.",
                        "default": False,
                    },
                },
                "required": ["agent_id"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "check_trust":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    agent_id = arguments["agent_id"]
    await db.init()
    score = await db.get_score(agent_id)

    if not score:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Agent {agent_id} not scored yet",
            "agent_id": agent_id,
        }))]

    return [TextContent(type="text", text=json.dumps(score, default=str))]


async def main():
    await db.init()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
