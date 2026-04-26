import asyncio
import json
import logging
from config import Settings
from db import Database
from agent.chain import ChainFetcher, RPCPool
from agent.trust_engine import TrustEngine
from agent.sybil import SybilDetector
from agent.contagion import ContagionEngine
from agent.publisher import Publisher
from agent.discovery import Discovery
from agent.alerts import AlertChecker
from agent.erc8004 import ERC8004Client
from agent.paymaster import PaymasterTransactor
from agent.validator import Validator
from agent.graph import TrustGraph
from agent.analyzers.longevity import LongevityAnalyzer
from agent.analyzers.activity import ActivityAnalyzer
from agent.analyzers.counterparty import CounterpartyAnalyzer
from agent.analyzers.contract_risk import ContractRiskAnalyzer
from agent.analyzers.agent_identity import AgentIdentityAnalyzer
from web3 import Web3

logger = logging.getLogger(__name__)

STAKING_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"uint8","name":"score","type":"uint8"}],"name":"stakeScore","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"},{"internalType":"uint8","name":"prev","type":"uint8"},{"internalType":"uint8","name":"next","type":"uint8"}],"name":"emitTrustDegraded","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

TRUSTGATE_ABI = json.loads('[{"inputs":[{"internalType":"uint256[]","name":"agentIds","type":"uint256[]"},{"internalType":"uint8[]","name":"scores","type":"uint8[]"},{"internalType":"string[]","name":"evidenceURIs","type":"string[]"}],"name":"batchUpdateTrust","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getTrustRecord","outputs":[{"internalType":"uint8","name":"score","type":"uint8"},{"internalType":"uint8","name":"verdict","type":"uint8"},{"internalType":"uint40","name":"updatedAt","type":"uint40"},{"internalType":"string","name":"evidenceURI","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"isTrusted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalScored","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getTrustScore","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"agentId","type":"uint256"}],"name":"getVerdict","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]')


class SentinelNetAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database()

        # Parse multi-RPC URL lists (fall back to single URL for backwards compat)
        base_rpc_urls = [u.strip() for u in settings.BASE_RPC_URLS.split(",") if u.strip()] if settings.BASE_RPC_URLS else []
        eth_rpc_urls = [u.strip() for u in settings.ETH_RPC_URLS.split(",") if u.strip()] if settings.ETH_RPC_URLS else []
        # If no multi-URL list, fall back to single URL
        if not base_rpc_urls:
            base_rpc_urls = [settings.BASE_RPC_URL]
        if not eth_rpc_urls:
            eth_rpc_urls = [settings.ETH_RPC_URL]

        self.chain = ChainFetcher(
            settings.BASE_RPC_URL, settings.ETH_RPC_URL,
            basescan_api_key=settings.BASESCAN_API_KEY,
            etherscan_api_key=settings.ETHERSCAN_API_KEY,
            base_rpc_urls=base_rpc_urls,
            eth_rpc_urls=eth_rpc_urls,
        )
        self.engine = TrustEngine()
        self.sybil = SybilDetector()
        self.contagion = ContagionEngine()
        self.alerts = AlertChecker()

        # Analyzers
        self.longevity = LongevityAnalyzer()
        self.activity = ActivityAnalyzer()
        self.counterparty_analyzer = CounterpartyAnalyzer()
        self.contract_risk_analyzer = ContractRiskAnalyzer()
        self.identity_analyzer = AgentIdentityAnalyzer()

        # Wallet sharing tracker (populated during sweeps)
        self._wallet_agent_count = {}
        # Sybil detection: edges collected during sweep for batch analysis
        self._sweep_edges = {}
        self._wallet_to_agent = {}
        self._sybil_flagged = set()
        # Wallet → [agent_ids] for sybil wallet-sharing detection
        self._wallet_agents = {}

        # Web3 + ERC-8004 (use Base RPC pool for main w3 instance)
        self.base_pool = RPCPool(base_rpc_urls, chain_name="base-main")
        self.w3 = self.base_pool.get_web3()
        logger.info(f"Base RPC pool: {len(base_rpc_urls)} URLs, active: {self.base_pool.active_url}")
        logger.info(f"ETH RPC pool: {len(eth_rpc_urls)} URLs")

        # Paymaster for gasless transactions
        self.paymaster = None
        if settings.CDP_API_KEY_ID and settings.CDP_API_SECRET:
            self.paymaster = PaymasterTransactor(
                api_key_id=settings.CDP_API_KEY_ID,
                api_secret=settings.CDP_API_SECRET,
                smart_account_address=settings.CDP_SMART_ACCOUNT,
                paymaster_url=settings.CDP_PAYMASTER_URL,
                private_key=settings.PRIVATE_KEY,
            )
            logger.info("CDP Paymaster initialized for gasless transactions")

        self.erc8004 = ERC8004Client(
            w3=self.w3,
            identity_addr=settings.IDENTITY_REGISTRY,
            reputation_addr=settings.REPUTATION_REGISTRY,
            validation_addr=settings.VALIDATION_REGISTRY,
            private_key=settings.PRIVATE_KEY,
            agent_id=settings.SENTINELNET_AGENT_ID,
            paymaster=self.paymaster,
        )

        # Staking contract
        self.staking = None
        if settings.STAKING_CONTRACT and settings.PRIVATE_KEY:
            try:
                self.staking = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.STAKING_CONTRACT),
                    abi=STAKING_ABI,
                )
            except Exception as e:
                logger.warning(f"Failed to init staking contract: {e}")

        # TrustGate on-chain oracle
        self.trustgate = None
        if settings.TRUSTGATE_CONTRACT and settings.PRIVATE_KEY:
            try:
                self.trustgate = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.TRUSTGATE_CONTRACT),
                    abi=TRUSTGATE_ABI,
                )
                logger.info(f"TrustGate initialized at {settings.TRUSTGATE_CONTRACT}")
            except Exception as e:
                logger.warning(f"Failed to init TrustGate contract: {e}")

        # Sweep score collector for TrustGate batch updates
        self._sweep_scores = []

        # EAS attestor
        self.eas = None
        if settings.PRIVATE_KEY and settings.EAS_SCHEMA_UID:
            try:
                from agent.eas import EASAttestor
                self.eas = EASAttestor(
                    w3=self.w3,
                    private_key=settings.PRIVATE_KEY,
                    schema_uid=settings.EAS_SCHEMA_UID,
                )
                logger.info("EAS attestor initialized")
            except Exception as e:
                logger.warning(f"Failed to init EAS attestor: {e}")

        # Publisher
        self.publisher = Publisher(
            pinata_api_key=settings.PINATA_API_KEY,
            pinata_secret_key=settings.PINATA_SECRET_KEY,
            erc8004_client=self.erc8004,
            pinata_jwt=settings.PINATA_JWT,
            lighthouse_api_key=settings.LIGHTHOUSE_API_KEY,
            scorer_address=self.erc8004.account.address if self.erc8004.account else "",
        )

        # Graph
        self.graph = TrustGraph(self.db)

    async def start(self):
        await self.db.init()
        logger.info("SentinelNet agent started")

        # Load wallet→agents map for sybil wallet-sharing detection
        self._wallet_agents = await self.db.get_wallet_agent_map()

        self.discovery = Discovery(
            erc8004=self.erc8004,
            db=self.db,
            pipeline=self.analyze_agent,
            self_agent_id=self.settings.SENTINELNET_AGENT_ID,
            sweep_interval=self.settings.SWEEP_INTERVAL_SECONDS,
            on_sweep_complete=self._run_post_sweep,
        )

        self.validator = Validator(
            erc8004=self.erc8004,
            pipeline=self.analyze_agent,
            publisher=self.publisher,
        )

        asyncio.create_task(self.discovery.run_loop())
        logger.info("Discovery sweep loop started")

    async def _run_post_sweep(self):
        """Run sybil detection + contagion propagation + TrustGate batch update after each sweep."""
        await self._run_sybil_detection()
        await self._run_contagion()
        await self._update_trustgate_batch()

    async def _update_trustgate_batch(self):
        """Batch-update TrustGate on-chain with scores from this sweep.

        Routes through CDP Paymaster (gasless) when available.
        Falls back to direct EOA transactions if paymaster is not configured.
        Batch size 25 to amortize base gas cost across more agents.
        """
        if not self.trustgate or not self._sweep_scores or not self.erc8004.account:
            self._sweep_scores = []
            return
        try:
            BATCH_SIZE = 25
            written = 0
            use_paymaster = (self.paymaster and self.paymaster.enabled)

            for i in range(0, len(self._sweep_scores), BATCH_SIZE):
                batch = self._sweep_scores[i:i + BATCH_SIZE]
                agent_ids = [s[0] for s in batch]
                scores = [min(s[1], 100) for s in batch]
                evidence_uris = [s[2] for s in batch]

                try:
                    paymaster_ok = False
                    if use_paymaster:
                        # Gasless via CDP Paymaster
                        try:
                            data = self.trustgate.functions.batchUpdateTrust(
                                agent_ids, scores, evidence_uris
                            )._encode_transaction_data()
                            tx_hash = await self.paymaster.send_call(
                                to=self.trustgate.address, data=data
                            )
                            if tx_hash:
                                written += len(batch)
                                paymaster_ok = True
                                logger.info(
                                    f"TrustGate paymaster batch {i // BATCH_SIZE + 1} "
                                    f"({len(batch)} agents): {tx_hash}"
                                )
                            else:
                                logger.warning(
                                    f"TrustGate paymaster batch {i // BATCH_SIZE + 1} "
                                    f"returned empty hash, falling back to EOA"
                                )
                        except Exception as pm_err:
                            logger.warning(
                                f"TrustGate paymaster batch {i // BATCH_SIZE + 1} "
                                f"failed, falling back to EOA: {pm_err}"
                            )
                            use_paymaster = False

                    if not paymaster_ok:
                        # Direct EOA fallback
                        sender = self.erc8004.account.address
                        balance = await asyncio.to_thread(
                            self.w3.eth.get_balance, sender
                        )
                        if balance < self.w3.to_wei(0.0001, "ether"):
                            logger.warning(
                                f"TrustGate: insufficient balance "
                                f"({self.w3.from_wei(balance, 'ether')} ETH), "
                                f"stopping after {written} agents"
                            )
                            break

                        nonce = await asyncio.to_thread(
                            self.w3.eth.get_transaction_count, sender, "pending",
                        )
                        gas_price = await asyncio.to_thread(
                            lambda: self.w3.eth.gas_price
                        )
                        tx_params = {
                            "from": sender,
                            "nonce": nonce,
                            "gasPrice": int(gas_price * 1.1),
                            "chainId": 8453,
                            "gas": 80000 + 55000 * len(batch),
                        }
                        tx = self.trustgate.functions.batchUpdateTrust(
                            agent_ids, scores, evidence_uris
                        ).build_transaction(tx_params)
                        signed = self.w3.eth.account.sign_transaction(
                            tx, self.settings.PRIVATE_KEY
                        )
                        tx_hash = await asyncio.to_thread(
                            self.w3.eth.send_raw_transaction, signed.raw_transaction
                        )
                        written += len(batch)
                        logger.info(
                            f"TrustGate EOA batch {i // BATCH_SIZE + 1} "
                            f"({len(batch)} agents): {tx_hash.hex()}"
                        )

                    # Brief delay between batches to avoid rate limits
                    if i + BATCH_SIZE < len(self._sweep_scores):
                        await asyncio.sleep(2)

                except Exception as e:
                    logger.warning(f"TrustGate batch {i // BATCH_SIZE + 1} failed: {e}")

            if written:
                logger.info(f"TrustGate: {written}/{len(self._sweep_scores)} agents written on-chain")

        except Exception as e:
            logger.warning(f"TrustGate batch update failed: {e}")
        finally:
            self._sweep_scores = []

    async def _run_sybil_detection(self):
        """Run sybil detection after each sweep using collected edges."""
        if not self._sweep_edges:
            return

        # Refresh wallet→agents map
        self._wallet_agents = await self.db.get_wallet_agent_map()

        clusters = self.sybil.detect(
            self._sweep_edges,
            self._wallet_to_agent,
            wallet_agent_count=self._wallet_agents,
        )
        if clusters:
            flagged = set()
            for cluster in clusters:
                flagged.update(cluster)
                logger.warning(f"Sybil cluster detected: {cluster}")
                # Record threat
                await self.db.save_threat(
                    "SYBIL_CLUSTER", "HIGH", cluster[0],
                    f"Coordinated cluster of {len(cluster)} agents: {cluster}"
                )
            self._sybil_flagged = flagged
            # Re-score flagged agents with sybil penalty
            for agent_id in flagged:
                try:
                    existing = await self.db.get_score(agent_id)
                    if existing and not existing.get("sybil_flagged"):
                        await self.analyze_agent(agent_id, sybil_override=True)
                except Exception as e:
                    logger.error(f"Failed to re-score sybil agent {agent_id}: {e}")
        # Clear sweep edges for next cycle
        self._sweep_edges = {}
        self._wallet_to_agent = {}

    async def _run_contagion(self):
        """Run trust contagion propagation across the agent graph."""
        try:
            scores_list = await self.db.get_all_scores()
            if not scores_list:
                return
            scores = {s["agent_id"]: s for s in scores_list}
            edges = await self.db.get_all_edges()
            if not edges:
                return

            adjustments = self.contagion.compute_adjustments(scores, edges)
            if not adjustments:
                return

            for agent_id, adj in adjustments.items():
                s = scores.get(agent_id)
                if not s:
                    continue
                # Apply contagion adjustment to stored score
                base_score = s["trust_score"]
                new_score = max(0, min(100, base_score + adj))
                if new_score == base_score:
                    continue

                new_verdict = self.engine._verdict(new_score)

                # Record threat if significant negative contagion
                if adj <= -5:
                    await self.db.save_threat(
                        "TRUST_CONTAGION", "MEDIUM", agent_id,
                        f"Score adjusted by {adj} due to interactions with low-trust agents "
                        f"({base_score} -> {new_score})"
                    )

                # Update the score in DB with contagion adjustment.
                # IMPORTANT: pass attestation_uid through — save_score defaults
                # it to "" and would otherwise wipe a real EAS UID on every
                # contagion sweep.
                await self.db.save_score(
                    agent_id, s["wallet"], new_score,
                    s["longevity"], s["activity"], s["counterparty"],
                    s["contract_risk"], new_verdict, s.get("feedback_tx", ""),
                    s.get("evidence_uri", ""),
                    agent_identity=s.get("agent_identity", 0),
                    sybil_flagged=bool(s.get("sybil_flagged")),
                    contagion_adjustment=adj,
                    attestation_uid=s.get("attestation_uid", ""),
                )
                logger.info(f"Contagion applied to agent {agent_id}: {base_score} -> {new_score} (adj={adj})")

        except Exception as e:
            logger.error(f"Contagion propagation failed: {e}")

    async def _stake_score(self, agent_id: int, score: int, is_first_score: bool = True):
        """Stake ETH behind a published score. Skipped on rescores by default —
        the original audit math at STAKE_AMOUNT_ETH=0.001 with 30-min sweeps
        would have burned ~10 ETH/day staking the same agents repeatedly.
        Toggle with `STAKE_ON_RESCORE=true` if a wallet that can sustain it
        is funded.
        """
        if not self.staking or not self.erc8004.account:
            return
        if not self.settings.STAKING_ENABLED:
            return
        if not is_first_score and not self.settings.STAKE_ON_RESCORE:
            return
        try:
            balance = await asyncio.to_thread(
                self.w3.eth.get_balance, self.erc8004.account.address
            )
            stake_wei = self.w3.to_wei(self.settings.STAKE_AMOUNT_ETH, "ether")
            if balance < stake_wei + self.w3.to_wei(0.001, "ether"):
                logger.debug(f"Insufficient balance for staking agent {agent_id}, skipping")
                return

            nonce = await asyncio.to_thread(
                self.w3.eth.get_transaction_count, self.erc8004.account.address
            )
            tx = self.staking.functions.stakeScore(
                agent_id, min(score, 255)
            ).build_transaction({
                "from": self.erc8004.account.address,
                "value": stake_wei,
                "nonce": nonce,
                "gas": 150000,
                "maxFeePerGas": self.w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.settings.PRIVATE_KEY)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"Staked {self.settings.STAKE_AMOUNT_ETH} ETH on agent {agent_id} score={score}: {tx_hash.hex()}")
        except Exception as e:
            logger.warning(f"Staking failed for agent {agent_id}: {e}")

    async def _emit_trust_degraded(self, agent_id: int, prev_score: int, new_score: int):
        """Emit TrustDegraded event on-chain."""
        if not self.staking or not self.erc8004.account:
            return

        # Try paymaster first (gasless)
        if self.paymaster and self.paymaster.enabled:
            try:
                data = self.staking.encode_abi(
                    abi_element_identifier="emitTrustDegraded",
                    args=[agent_id, min(prev_score, 255), min(new_score, 255)],
                )
                tx_hash = await self.paymaster.send_call(
                    to=self.settings.STAKING_CONTRACT, data=data
                )
                if tx_hash:
                    logger.info(f"TrustDegraded via paymaster for agent {agent_id}: {prev_score}->{new_score} tx={tx_hash}")
                    return
            except Exception as e:
                logger.warning(f"Paymaster emitTrustDegraded failed, falling back: {e}")

        # Fallback: direct EOA transaction
        try:
            balance = await asyncio.to_thread(
                self.w3.eth.get_balance, self.erc8004.account.address
            )
            if balance < self.w3.to_wei(0.001, "ether"):
                logger.debug(f"Insufficient balance for emitTrustDegraded agent {agent_id}, skipping")
                return

            nonce = await asyncio.to_thread(
                self.w3.eth.get_transaction_count, self.erc8004.account.address
            )
            tx = self.staking.functions.emitTrustDegraded(
                agent_id, min(prev_score, 255), min(new_score, 255)
            ).build_transaction({
                "from": self.erc8004.account.address,
                "nonce": nonce,
                "gas": 100000,
                "maxFeePerGas": self.w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, "gwei"),
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.settings.PRIVATE_KEY)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed.raw_transaction
            )
            logger.info(f"TrustDegraded emitted on-chain for agent {agent_id}: {prev_score}->{new_score} tx={tx_hash.hex()}")
        except Exception as e:
            logger.warning(f"emitTrustDegraded failed for agent {agent_id}: {e}")

    async def _attest_trust(self, agent_id: int, trust_score: int,
                            verdict: str, evidence_uri: str, wallet: str,
                            sybil_flagged: bool) -> str:
        """Create EAS attestation for a trust score."""
        if not self.eas:
            return ""
        try:
            uid = await self.eas.attest_trust(
                agent_id, trust_score, verdict, evidence_uri, wallet, sybil_flagged
            )
            return uid
        except Exception as e:
            logger.warning(f"EAS attestation failed for agent {agent_id}: {e}")
            return ""

    async def analyze_agent(self, agent_id: int, sybil_override: bool = False) -> dict:
        wallet = await self.erc8004.get_agent_wallet(agent_id)
        if not wallet:
            logger.warning(f"No wallet found for agent {agent_id}")
            return None

        data = await self.chain.fetch_wallet(wallet)

        # Track wallet→agents for sybil wallet-sharing detection and identity scoring
        wallet_lower = wallet.lower()
        self._wallet_agents.setdefault(wallet_lower, [])
        if agent_id not in self._wallet_agents[wallet_lower]:
            self._wallet_agents[wallet_lower].append(agent_id)
        agents_sharing = len(self._wallet_agents[wallet_lower])

        # Collect edges for sybil detection (batch processed after sweep)
        self._sweep_edges[agent_id] = set(data.counterparties)
        self._wallet_to_agent[wallet_lower] = agent_id

        # Fetch agent-level identity signals
        has_metadata = False
        metadata_fields = 0
        try:
            uri = await self.erc8004.get_agent_uri(agent_id)
            if uri:
                parsed = self.erc8004._parse_registration_json(uri)
                if parsed:
                    has_metadata = True
                    for key in ["name", "description", "image", "external_url",
                                "service_endpoint", "operator", "capabilities"]:
                        val = parsed.get(key)
                        if val and val != "" and val != []:
                            metadata_fields += 1
        except Exception:
            pass

        # Fetch on-chain reputation for this agent (ALL feedback, not just ours)
        rep_count = 0
        rep_value = 0
        try:
            rep_data = await self.erc8004.get_agent_reputation(agent_id)
            rep_count = rep_data.get("count", 0)
            rep_value = rep_data.get("value", 0)
        except Exception:
            pass

        longevity = self.longevity.score(data.wallet_age_days, data.wallet_age_days)
        activity = self.activity.score(
            data.tx_count, data.active_days, data.total_days,
            eth_balance=data.eth_balance,
            tx_timestamps=data.tx_timestamps,
        )
        counterparty = self.counterparty_analyzer.score(
            len(data.counterparties), data.verified_counterparties, data.flagged_counterparties,
            funding_source=data.funding_source,
        )
        contract_risk = self.contract_risk_analyzer.score(
            len(data.contracts), data.malicious_contracts, data.unverified_contracts
        )
        agent_identity = self.identity_analyzer.score(
            has_metadata, metadata_fields, rep_count, rep_value, agents_sharing
        )

        # Check sybil status
        is_sybil = sybil_override or agent_id in self._sybil_flagged

        result = self.engine.compute(
            longevity, activity, counterparty, contract_risk,
            agent_identity=agent_identity,
            sybil_risk=is_sybil,
        )

        # Check for trust degradation
        existing = await self.db.get_score(agent_id)
        if existing:
            prev_score = existing["trust_score"]
            if self.alerts.should_alert(prev_score, result.trust_score):
                logger.warning(f"TrustDegraded: agent {agent_id} dropped {prev_score} -> {result.trust_score}")
                await self._emit_trust_degraded(agent_id, prev_score, result.trust_score)
                # Record threat
                await self.db.save_threat(
                    "TRUST_DEGRADED", "HIGH", agent_id,
                    f"Trust score dropped from {prev_score} to {result.trust_score}"
                )

        # Publish to chain + IPFS
        pub_result = await self.publisher.publish(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk, result.verdict,
            agent_identity=agent_identity,
        )

        # Stake ETH behind the score (first-score only by default — see _stake_score docstring)
        await self._stake_score(agent_id, result.trust_score, is_first_score=(existing is None))

        # EAS attestation
        attestation_uid = await self._attest_trust(
            agent_id, result.trust_score, result.verdict,
            pub_result.get("evidence_uri", ""), wallet, is_sybil
        )

        # Save to local cache
        await self.db.save_score(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk,
            result.verdict, pub_result.get("feedback_txs", [""])[0],
            pub_result.get("evidence_uri", ""),
            agent_identity=agent_identity,
            sybil_flagged=is_sybil,
            attestation_uid=attestation_uid,
        )

        # Collect for TrustGate batch update
        self._sweep_scores.append((agent_id, result.trust_score, pub_result.get("evidence_uri", "")))

        # Save graph edges
        for cp in data.counterparties:
            await self.db.save_edge(agent_id, cp, 1, False)

        logger.info(f"Scored agent {agent_id}: {result.trust_score} ({result.verdict}) [L={longevity} A={activity} C={counterparty} R={contract_risk} I={agent_identity}]{' SYBIL' if is_sybil else ''}")
        return result
