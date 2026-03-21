import asyncio
import logging
import uvicorn
from config import Settings
from agent import SentinelNetAgent
from api import app, db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("sentinelnet")


async def main():
    settings = Settings()
    agent = SentinelNetAgent(settings)

    # Share the agent's db with the API and MCP
    import api as api_module
    api_module.db = agent.db
    try:
        import mcp.server as mcp_module
        mcp_module.db = agent.db
        mcp_module._agent_ref = agent
    except Exception:
        pass

    # Start agent
    await agent.start()
    logger.info("SentinelNet agent running")

    # Score ourselves on startup (non-blocking)
    async def _self_score():
        try:
            await asyncio.sleep(5)  # Let sweep start first
            result = await agent.analyze_agent(settings.SENTINELNET_AGENT_ID)
            if result:
                logger.info(f"Self-score complete: {result.trust_score} ({result.verdict})")
        except Exception as e:
            logger.warning(f"Self-score failed: {e}")
    asyncio.create_task(_self_score())

    # Start API server
    config = uvicorn.Config(app, host="0.0.0.0", port=8004, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
