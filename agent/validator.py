import logging

logger = logging.getLogger(__name__)


class Validator:
    def __init__(self, erc8004, pipeline, publisher):
        self.erc8004 = erc8004
        self.pipeline = pipeline
        self.publisher = publisher

    async def handle_validation_request(self, request_hash: bytes, agent_id: int) -> dict:
        """Run full pipeline on demand and post validation response."""
        logger.info(f"Validation request for agent {agent_id}")
        result = await self.pipeline(agent_id)
        if result is None:
            logger.warning(f"Could not score agent {agent_id}")
            return {"error": "Agent not found"}

        response_uri = ""
        if self.publisher:
            pub = await self.publisher.publish(
                agent_id, "", result.trust_score,
                result.longevity, result.activity,
                result.counterparty, result.contract_risk, result.verdict,
            )
            response_uri = pub.get("evidence_uri", "")

        tx = await self.erc8004.validation_response(
            request_hash, result.trust_score,
            response_uri, b"\x00" * 32, "trust-assessment"
        )

        return {
            "agent_id": agent_id,
            "trust_score": result.trust_score,
            "verdict": result.verdict,
            "validation_tx": tx,
        }
