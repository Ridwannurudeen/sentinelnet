import json
from typing import Optional, List
from web3 import Web3


class ERC8004Client:
    def __init__(self, w3: Web3, identity_addr: str,
                 reputation_addr: str, validation_addr: str,
                 private_key: str, agent_id: int):
        self.w3 = w3
        self.identity_addr = Web3.to_checksum_address(identity_addr)
        self.reputation_addr = Web3.to_checksum_address(reputation_addr) if reputation_addr else None
        self.validation_addr = Web3.to_checksum_address(validation_addr) if validation_addr else None
        self.private_key = private_key
        self.agent_id = agent_id
        self.account = w3.eth.account.from_key(private_key) if private_key else None

    async def get_total_agents(self) -> int:
        """Get total registered agents from Identity Registry."""
        return 0

    async def get_agent_wallet(self, agent_id: int) -> Optional[str]:
        """Get wallet address for an agent from Identity Registry."""
        return None

    async def get_agent_uri(self, agent_id: int) -> Optional[str]:
        """Get registration URI for an agent."""
        return None

    async def give_feedback(self, agent_id: int, value: int, tag1: str,
                           tag2: str, feedback_uri: str, feedback_hash: bytes) -> str:
        """Post feedback to Reputation Registry. Returns tx hash."""
        params = self._build_feedback_params(agent_id, value, tag1, tag2,
                                              feedback_uri, feedback_hash)
        return ""

    async def validation_response(self, request_hash: bytes, response: int,
                                  response_uri: str, response_hash: bytes,
                                  tag: str) -> str:
        """Post validation response. Returns tx hash."""
        return ""

    def _parse_registration_json(self, raw: str) -> dict:
        return json.loads(raw)

    def _build_feedback_params(self, agent_id: int, value: int, tag1: str,
                                tag2: str, feedback_uri: str,
                                feedback_hash: bytes) -> dict:
        return {
            "agent_id": agent_id,
            "value": value,
            "value_decimals": 0,
            "tag1": tag1,
            "tag2": tag2,
            "feedback_uri": feedback_uri,
            "feedback_hash": feedback_hash,
        }
