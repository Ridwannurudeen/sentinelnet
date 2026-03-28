import asyncio
import json
import logging
from typing import Optional
from web3 import Web3

logger = logging.getLogger(__name__)

# Minimal ABIs for ERC-8004 contracts (behind ERC1967 proxies)
IDENTITY_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"tokenURI","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getAgentWallet","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"string","name":"newURI","type":"string"}],"name":"setAgentURI","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"address","name":"newWallet","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bytes","name":"signature","type":"bytes"}],"name":"setAgentWallet","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

REPUTATION_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getClients","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"address","name":"client","type":"address"}],"name":"getLastIndex","outputs":[{"internalType":"uint64","name":"","type":"uint64"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"address","name":"client","type":"address"},{"internalType":"uint64","name":"index","type":"uint64"}],"name":"readFeedback","outputs":[{"internalType":"int128","name":"value","type":"int128"},{"internalType":"uint8","name":"decimals","type":"uint8"},{"internalType":"string","name":"tag1","type":"string"},{"internalType":"string","name":"tag2","type":"string"},{"internalType":"bool","name":"isRevoked","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"int128","name":"value","type":"int128"},{"internalType":"uint8","name":"valueDecimals","type":"uint8"},{"internalType":"string","name":"tag1","type":"string"},{"internalType":"string","name":"tag2","type":"string"},{"internalType":"string","name":"endpoint","type":"string"},{"internalType":"string","name":"feedbackURI","type":"string"},{"internalType":"bytes32","name":"feedbackHash","type":"bytes32"}],"name":"giveFeedback","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"getIdentityRegistry","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"address[]","name":"clients","type":"address[]"},{"internalType":"string","name":"tag1","type":"string"},{"internalType":"string","name":"tag2","type":"string"}],"name":"getSummary","outputs":[{"internalType":"uint64","name":"count","type":"uint64"},{"internalType":"int128","name":"summaryValue","type":"int128"},{"internalType":"uint8","name":"decimals","type":"uint8"}],"stateMutability":"view","type":"function"}]')

VALIDATION_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"validatorAddress","type":"address"},{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"string","name":"requestURI","type":"string"},{"internalType":"bytes32","name":"requestHash","type":"bytes32"}],"name":"validationRequest","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"requestHash","type":"bytes32"},{"internalType":"uint8","name":"response","type":"uint8"},{"internalType":"string","name":"responseURI","type":"string"},{"internalType":"bytes32","name":"responseHash","type":"bytes32"},{"internalType":"string","name":"tag","type":"string"}],"name":"validationResponse","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"requestHash","type":"bytes32"}],"name":"getValidationStatus","outputs":[{"internalType":"address","name":"validatorAddress","type":"address"},{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"uint8","name":"response","type":"uint8"},{"internalType":"bytes32","name":"responseHash","type":"bytes32"},{"internalType":"string","name":"tag","type":"string"},{"internalType":"uint256","name":"lastUpdate","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"address[]","name":"validatorAddresses","type":"address[]"},{"internalType":"string","name":"tag","type":"string"}],"name":"getSummary","outputs":[{"internalType":"uint64","name":"count","type":"uint64"},{"internalType":"uint8","name":"averageResponse","type":"uint8"}],"stateMutability":"view","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"validatorAddress","type":"address"},{"indexed":true,"internalType":"uint256","name":"agentId","type":"uint256"},{"indexed":false,"internalType":"string","name":"requestURI","type":"string"},{"indexed":true,"internalType":"bytes32","name":"requestHash","type":"bytes32"}],"name":"ValidationRequest","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"validatorAddress","type":"address"},{"indexed":true,"internalType":"uint256","name":"agentId","type":"uint256"},{"indexed":true,"internalType":"bytes32","name":"requestHash","type":"bytes32"},{"internalType":"uint8","name":"response","type":"uint8"},{"internalType":"string","name":"responseURI","type":"string"},{"internalType":"bytes32","name":"responseHash","type":"bytes32"},{"internalType":"string","name":"tag","type":"string"}],"name":"ValidationResponse","type":"event"}]')


class ERC8004Client:
    def __init__(self, w3: Web3, identity_addr: str,
                 reputation_addr: str, validation_addr: str,
                 private_key: str, agent_id: int, paymaster=None):
        self.w3 = w3
        self.identity_addr = Web3.to_checksum_address(identity_addr)
        self.reputation_addr = Web3.to_checksum_address(reputation_addr) if reputation_addr else None
        self.validation_addr = Web3.to_checksum_address(validation_addr) if validation_addr else None
        self.private_key = private_key
        self.agent_id = agent_id
        self.account = w3.eth.account.from_key(private_key) if private_key else None
        self.paymaster = paymaster

        self.identity = w3.eth.contract(address=self.identity_addr, abi=IDENTITY_ABI)
        if self.reputation_addr:
            self.reputation = w3.eth.contract(address=self.reputation_addr, abi=REPUTATION_ABI)
        else:
            self.reputation = None
        if self.validation_addr:
            self.validation = w3.eth.contract(address=Web3.to_checksum_address(self.validation_addr), abi=VALIDATION_ABI)
        else:
            self.validation = None
        self._nonce_lock = asyncio.Lock()
        self._current_nonce = None

    async def get_total_agents(self) -> int:
        """Get total registered agents from Identity Registry via totalSupply."""
        try:
            total = await asyncio.to_thread(self.identity.functions.totalSupply().call)
            return total
        except Exception as e:
            logger.warning(f"totalSupply failed, falling back to estimate: {e}")
            # Fallback: try to binary search for the highest valid tokenId
            return await self._estimate_total_agents()

    async def _estimate_total_agents(self) -> int:
        """Binary search for highest valid agent ID."""
        low, high = 1, 40000
        while low < high:
            mid = (low + high + 1) // 2
            try:
                await asyncio.to_thread(self.identity.functions.ownerOf(mid).call)
                low = mid
            except Exception:
                high = mid - 1
        return low

    async def get_agent_wallet(self, agent_id: int) -> Optional[str]:
        """Get wallet address for an agent. Tries getAgentWallet first, falls back to ownerOf."""
        try:
            wallet = await asyncio.to_thread(
                self.identity.functions.getAgentWallet(agent_id).call
            )
            if wallet and wallet != "0x0000000000000000000000000000000000000000":
                return wallet
        except Exception:
            pass

        try:
            owner = await asyncio.to_thread(
                self.identity.functions.ownerOf(agent_id).call
            )
            if owner and owner != "0x0000000000000000000000000000000000000000":
                return owner
        except Exception as e:
            logger.warning(f"Failed to get wallet for agent {agent_id}: {e}")
        return None

    async def get_agent_uri(self, agent_id: int) -> Optional[str]:
        """Get registration URI for an agent."""
        try:
            uri = await asyncio.to_thread(
                self.identity.functions.tokenURI(agent_id).call
            )
            return uri
        except Exception as e:
            logger.warning(f"Failed to get URI for agent {agent_id}: {e}")
            return None

    async def set_agent_uri(self, agent_id: int, new_uri: str) -> str:
        """Update the agentURI on the Identity Registry. Returns tx hash."""
        if not self.account:
            logger.warning("No account configured for setAgentURI")
            return ""
        try:
            nonce = await asyncio.to_thread(
                self.w3.eth.get_transaction_count, self.account.address
            )
            tx = self.identity.functions.setAgentURI(agent_id, new_uri).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "maxFeePerGas": self.w3.to_wei(0.15, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"setAgentURI tx for agent {agent_id}: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to set agent URI for {agent_id}: {e}")
            return ""

    async def get_existing_feedback(self, agent_id: int) -> dict:
        """Check if we already gave feedback to this agent."""
        if not self.reputation or not self.account:
            return {"count": 0}
        try:
            last_idx = await asyncio.to_thread(
                self.reputation.functions.getLastIndex(agent_id, self.account.address).call
            )
            return {"count": last_idx}
        except Exception:
            return {"count": 0}

    async def get_agent_reputation(self, agent_id: int) -> dict:
        """Get ALL feedback for an agent from ALL clients via getSummary().

        Returns {"count": total_feedback_count, "value": net_sentiment_value}.
        """
        if not self.reputation:
            return {"count": 0, "value": 0}
        try:
            # Get all clients who gave feedback to this agent
            clients = await asyncio.to_thread(
                self.reputation.functions.getClients(agent_id).call
            )
            if not clients:
                return {"count": 0, "value": 0}
            # Get aggregate summary across all clients
            count, summary_value, decimals = await asyncio.to_thread(
                self.reputation.functions.getSummary(agent_id, clients, "", "").call
            )
            return {"count": int(count), "value": int(summary_value)}
        except Exception as e:
            logger.debug(f"getSummary failed for agent {agent_id}: {e}")
            return {"count": 0, "value": 0}

    async def give_feedback(self, agent_id: int, value: int, tag1: str,
                           tag2: str, feedback_uri: str, feedback_hash: bytes) -> str:
        """Post feedback to Reputation Registry. Returns tx hash."""
        if not self.reputation or not self.account:
            logger.warning("No reputation registry or account configured")
            return ""

        # Ensure feedback_hash is bytes32
        if isinstance(feedback_hash, bytes) and len(feedback_hash) < 32:
            feedback_hash = feedback_hash.ljust(32, b'\x00')
        elif isinstance(feedback_hash, bytes) and len(feedback_hash) > 32:
            feedback_hash = feedback_hash[:32]

        args = [agent_id, value, 0, tag1, tag2, "", feedback_uri, feedback_hash]

        # Try paymaster first (gasless via CDP Smart Account)
        if self.paymaster and self.paymaster.enabled:
            try:
                data = self.reputation.encode_abi(abi_element_identifier="giveFeedback", args=args)
                tx_hash = await self.paymaster.send_call(to=self.reputation_addr, data=data)
                if tx_hash:
                    logger.info(f"Feedback via paymaster for agent {agent_id} tag={tag1}: {tx_hash}")
                    return tx_hash
            except Exception as e:
                logger.warning(f"Paymaster feedback failed for agent {agent_id}, falling back to EOA: {e}")

        # Fallback: direct EOA transaction (requires ETH for gas)
        try:
            async with self._nonce_lock:
                if self._current_nonce is None:
                    self._current_nonce = await asyncio.to_thread(
                        self.w3.eth.get_transaction_count, self.account.address
                    )
                nonce = self._current_nonce
                self._current_nonce += 1

            tx = self.reputation.functions.giveFeedback(*args).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 300000,
                "maxFeePerGas": self.w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"Feedback tx sent for agent {agent_id} tag={tag1}: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to send feedback for agent {agent_id}: {e}")
            return ""

    async def give_feedback_batch(self, feedbacks: list) -> list:
        """Send multiple giveFeedback calls in a single paymaster UserOp.

        Args:
            feedbacks: list of (agent_id, value, tag1, tag2, feedback_uri, feedback_hash)

        Returns:
            List of tx hashes.
        """
        if not self.reputation or not self.paymaster or not self.paymaster.enabled:
            # Fall back to individual calls
            results = []
            for f in feedbacks:
                r = await self.give_feedback(*f)
                results.append(r)
            return results

        calls = []
        for agent_id, value, tag1, tag2, feedback_uri, feedback_hash in feedbacks:
            if isinstance(feedback_hash, bytes) and len(feedback_hash) < 32:
                feedback_hash = feedback_hash.ljust(32, b'\x00')
            elif isinstance(feedback_hash, bytes) and len(feedback_hash) > 32:
                feedback_hash = feedback_hash[:32]

            data = self.reputation.encode_abi(
                abi_element_identifier="giveFeedback",
                args=[agent_id, value, 0, tag1, tag2, "", feedback_uri, feedback_hash],
            )
            calls.append({"to": self.reputation_addr, "data": data})

        try:
            results = await self.paymaster.send_calls(calls)
            # Treat all-empty results as failure (paymaster returned but didn't submit)
            if not results or all(r == "" for r in results):
                raise RuntimeError("Paymaster returned empty results")
            logger.info(f"Batch feedback via paymaster: {len(calls)} calls -> {results[0] if results else 'none'}")
            return results
        except Exception as e:
            logger.warning(f"Batch paymaster failed, falling back to individual EOA: {e}")
            results = []
            for f in feedbacks:
                r = await self.give_feedback(*f)
                results.append(r)
            return results

    async def validation_response(self, request_hash: bytes, response: int,
                                  response_uri: str, response_hash: bytes,
                                  tag: str) -> str:
        """Post validation response to Validation Registry. Returns tx hash."""
        if not self.validation or not self.account:
            logger.warning("No validation registry or account configured")
            return ""

        # Ensure hashes are bytes32
        if isinstance(request_hash, bytes) and len(request_hash) < 32:
            request_hash = request_hash.ljust(32, b'\x00')
        if isinstance(response_hash, bytes) and len(response_hash) < 32:
            response_hash = response_hash.ljust(32, b'\x00')

        args = [request_hash, response, response_uri, response_hash, tag]

        # Try paymaster first
        if self.paymaster and self.paymaster.enabled:
            try:
                data = self.validation.encode_abi(abi_element_identifier="validationResponse", args=args)
                tx_hash = await self.paymaster.send_call(to=self.validation_addr, data=data)
                if tx_hash:
                    logger.info(f"Validation response via paymaster: {tx_hash}")
                    return tx_hash
            except Exception as e:
                logger.warning(f"Paymaster validation response failed, falling back: {e}")

        # Fallback: EOA
        try:
            async with self._nonce_lock:
                if self._current_nonce is None:
                    self._current_nonce = await asyncio.to_thread(
                        self.w3.eth.get_transaction_count, self.account.address
                    )
                nonce = self._current_nonce
                self._current_nonce += 1

            tx = self.validation.functions.validationResponse(*args).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "maxFeePerGas": self.w3.to_wei(0.15, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"Validation response tx: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Validation response failed: {e}")
            return ""

    async def get_validation_status(self, request_hash: bytes) -> dict:
        """Get validation status for a request."""
        if not self.validation:
            return {}
        try:
            result = await asyncio.to_thread(
                self.validation.functions.getValidationStatus(request_hash).call
            )
            return {
                "validator": result[0],
                "agent_id": result[1],
                "response": result[2],
                "response_hash": result[3].hex() if result[3] else "",
                "tag": result[4],
                "last_update": result[5],
            }
        except Exception as e:
            logger.debug(f"getValidationStatus failed: {e}")
            return {}

    def _parse_registration_json(self, raw: str) -> dict:
        """Parse ERC-8004 registration metadata from tokenURI.

        Handles both inline JSON and data:application/json;base64,... URIs.
        """
        import base64
        if raw.startswith("data:"):
            # data:application/json;base64,<base64data>
            _, encoded = raw.split(",", 1)
            return json.loads(base64.b64decode(encoded))
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
