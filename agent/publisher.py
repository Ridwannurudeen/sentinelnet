import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class Publisher:
    PINATA_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

    def __init__(self, pinata_api_key: str, pinata_secret_key: str,
                 erc8004_client=None, pinata_jwt: str = "",
                 base_url: str = "https://sentinelnet.gudman.xyz"):
        self.pinata_api_key = pinata_api_key
        self.pinata_secret_key = pinata_secret_key
        self.pinata_jwt = pinata_jwt
        self.erc8004 = erc8004_client
        self.base_url = base_url

    async def publish(self, agent_id: int, wallet: str, trust_score: int,
                      longevity: int, activity: int, counterparty: int,
                      contract_risk: int, verdict: str,
                      agent_identity: int = 0) -> dict:
        evidence = self._build_evidence(
            agent_id, wallet, trust_score, longevity, activity,
            counterparty, contract_risk, verdict, ["base", "ethereum"],
            agent_identity=agent_identity,
        )
        evidence_hash = hashlib.sha256(json.dumps(evidence).encode()).digest()

        # Try IPFS first, fall back to self-hosted evidence URI
        evidence_uri = ""
        if self.pinata_jwt or (self.pinata_api_key and self.pinata_secret_key):
            try:
                evidence_uri = await self.pin_json(evidence)
            except Exception as e:
                logger.warning(f"IPFS pin failed: {e}")

        # Fallback: self-hosted evidence endpoint with content hash
        if not evidence_uri:
            content_hash = hashlib.sha256(json.dumps(evidence).encode()).hexdigest()
            evidence_uri = f"{self.base_url}/evidence/{agent_id}?hash={content_hash[:16]}"

        tags = [
            ("trustScore", trust_score),
            ("longevity", longevity),
            ("activity", activity),
            ("counterparty", counterparty),
            ("contractRisk", contract_risk),
        ]
        tx_hashes = []
        if self.erc8004:
            # Batch all feedback calls via paymaster if available
            if hasattr(self.erc8004, 'paymaster') and self.erc8004.paymaster and self.erc8004.paymaster.enabled:
                feedbacks = [
                    (agent_id, value, tag, "sentinelnet-v1", evidence_uri, evidence_hash)
                    for tag, value in tags
                ]
                tx_hashes = await self.erc8004.give_feedback_batch(feedbacks)
            else:
                for tag, value in tags:
                    tx = await self.erc8004.give_feedback(
                        agent_id, value, tag, "sentinelnet-v1",
                        evidence_uri, evidence_hash,
                    )
                    tx_hashes.append(tx)

        return {
            "evidence_uri": evidence_uri,
            "feedback_txs": tx_hashes,
        }

    async def pin_json(self, data: dict) -> str:
        if self.pinata_jwt:
            headers = {
                "Authorization": f"Bearer {self.pinata_jwt}",
                "Content-Type": "application/json",
            }
        else:
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_key": self.pinata_secret_key,
            }
        resp = await self._http_post(
            self.PINATA_URL,
            json={"pinataContent": data},
            headers=headers,
        )
        return f"ipfs://{resp['IpfsHash']}"

    async def _http_post(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, **kwargs)
            r.raise_for_status()
            return r.json()

    def _build_evidence(self, agent_id, wallet, trust_score, longevity,
                        activity, counterparty, contract_risk, verdict, chains,
                        agent_identity=0):
        return {
            "agent_id": agent_id,
            "wallet": wallet,
            "trust_score": trust_score,
            "breakdown": {
                "longevity": longevity,
                "activity": activity,
                "counterparty_quality": counterparty,
                "contract_risk": contract_risk,
                "agent_identity": agent_identity,
            },
            "verdict": verdict,
            "chains_analyzed": chains,
            "scorer": "sentinelnet-v1",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
