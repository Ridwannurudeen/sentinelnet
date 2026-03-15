import json
import hashlib
from datetime import datetime, timezone
from typing import Optional
import httpx


class Publisher:
    PINATA_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

    def __init__(self, pinata_api_key: str, pinata_secret_key: str,
                 erc8004_client=None):
        self.pinata_api_key = pinata_api_key
        self.pinata_secret_key = pinata_secret_key
        self.erc8004 = erc8004_client

    async def publish(self, agent_id: int, wallet: str, trust_score: int,
                      longevity: int, activity: int, counterparty: int,
                      contract_risk: int, verdict: str) -> dict:
        evidence = self._build_evidence(
            agent_id, wallet, trust_score, longevity, activity,
            counterparty, contract_risk, verdict, ["base", "ethereum"]
        )
        evidence_uri = await self.pin_json(evidence)
        evidence_hash = hashlib.sha256(json.dumps(evidence).encode()).digest()

        tags = [
            ("trustScore", trust_score),
            ("longevity", longevity),
            ("activity", activity),
            ("counterparty", counterparty),
            ("contractRisk", contract_risk),
        ]
        tx_hashes = []
        if self.erc8004:
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
        resp = await self._http_post(
            self.PINATA_URL,
            json={"pinataContent": data},
            headers={
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_key": self.pinata_secret_key,
            },
        )
        return f"ipfs://{resp['IpfsHash']}"

    async def _http_post(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, **kwargs)
            r.raise_for_status()
            return r.json()

    def _build_evidence(self, agent_id, wallet, trust_score, longevity,
                        activity, counterparty, contract_risk, verdict, chains):
        return {
            "agent_id": agent_id,
            "wallet": wallet,
            "trust_score": trust_score,
            "breakdown": {
                "longevity": longevity,
                "activity": activity,
                "counterparty_quality": counterparty,
                "contract_risk": contract_risk,
            },
            "verdict": verdict,
            "chains_analyzed": chains,
            "scorer": "sentinelnet-v1",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
