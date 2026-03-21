import asyncio
import logging
from config import Settings
from db import Database
from agent.chain import ChainFetcher
from agent.trust_engine import TrustEngine
from agent.sybil import SybilDetector
from agent.publisher import Publisher
from agent.discovery import Discovery
from agent.alerts import AlertChecker
from agent.erc8004 import ERC8004Client
from agent.validator import Validator
from agent.graph import TrustGraph
from agent.analyzers.longevity import LongevityAnalyzer
from agent.analyzers.activity import ActivityAnalyzer
from agent.analyzers.counterparty import CounterpartyAnalyzer
from agent.analyzers.contract_risk import ContractRiskAnalyzer
from agent.analyzers.agent_identity import AgentIdentityAnalyzer
from web3 import Web3

logger = logging.getLogger(__name__)


class SentinelNetAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database()
        self.chain = ChainFetcher(
            settings.BASE_RPC_URL, settings.ETH_RPC_URL,
            basescan_api_key=settings.BASESCAN_API_KEY,
            etherscan_api_key=settings.ETHERSCAN_API_KEY,
        )
        self.engine = TrustEngine()
        self.sybil = SybilDetector()
        self.alerts = AlertChecker()

        # Analyzers
        self.longevity = LongevityAnalyzer()
        self.activity = ActivityAnalyzer()
        self.counterparty_analyzer = CounterpartyAnalyzer()
        self.contract_risk_analyzer = ContractRiskAnalyzer()
        self.identity_analyzer = AgentIdentityAnalyzer()

        # Wallet sharing tracker (populated during sweeps)
        self._wallet_agent_count = {}

        # Web3 + ERC-8004
        self.w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))
        self.erc8004 = ERC8004Client(
            w3=self.w3,
            identity_addr=settings.IDENTITY_REGISTRY,
            reputation_addr=settings.REPUTATION_REGISTRY,
            validation_addr=settings.VALIDATION_REGISTRY,
            private_key=settings.PRIVATE_KEY,
            agent_id=settings.SENTINELNET_AGENT_ID,
        )

        # Publisher
        self.publisher = Publisher(
            pinata_api_key=settings.PINATA_API_KEY,
            pinata_secret_key=settings.PINATA_SECRET_KEY,
            erc8004_client=self.erc8004,
            pinata_jwt=settings.PINATA_JWT,
        )

        # Graph
        self.graph = TrustGraph(self.db)

    async def start(self):
        await self.db.init()
        logger.info("SentinelNet agent started")

        self.discovery = Discovery(
            erc8004=self.erc8004,
            db=self.db,
            pipeline=self.analyze_agent,
            self_agent_id=self.settings.SENTINELNET_AGENT_ID,
            sweep_interval=self.settings.SWEEP_INTERVAL_SECONDS,
        )

        self.validator = Validator(
            erc8004=self.erc8004,
            pipeline=self.analyze_agent,
            publisher=self.publisher,
        )

        asyncio.create_task(self.discovery.run_loop())
        logger.info("Discovery sweep loop started")

    async def analyze_agent(self, agent_id: int) -> dict:
        wallet = await self.erc8004.get_agent_wallet(agent_id)
        if not wallet:
            logger.warning(f"No wallet found for agent {agent_id}")
            return None

        data = await self.chain.fetch_wallet(wallet)

        # Track wallet sharing for identity scoring
        wallet_lower = wallet.lower()
        self._wallet_agent_count[wallet_lower] = self._wallet_agent_count.get(wallet_lower, 0) + 1
        agents_sharing = self._wallet_agent_count[wallet_lower]

        # Fetch agent-level identity signals
        has_metadata = False
        metadata_fields = 0
        try:
            uri = await self.erc8004.get_agent_uri(agent_id)
            if uri:
                parsed = self.erc8004._parse_registration_json(uri)
                if parsed:
                    has_metadata = True
                    # Count ERC-8004 registration fields
                    for key in ["name", "description", "image", "external_url",
                                "service_endpoint", "operator", "capabilities"]:
                        val = parsed.get(key)
                        if val and val != "" and val != []:
                            metadata_fields += 1
        except Exception:
            pass

        # Fetch on-chain reputation for this agent
        rep_count = 0
        rep_value = 0
        try:
            rep_data = await self.erc8004.get_existing_feedback(agent_id)
            rep_count = rep_data.get("count", 0)
        except Exception:
            pass

        longevity = self.longevity.score(data.wallet_age_days, data.wallet_age_days)
        activity = self.activity.score(
            data.tx_count, data.active_days, data.total_days,
            eth_balance=data.eth_balance,
        )
        counterparty = self.counterparty_analyzer.score(
            len(data.counterparties), data.verified_counterparties, data.flagged_counterparties
        )
        contract_risk = self.contract_risk_analyzer.score(
            len(data.contracts), data.malicious_contracts, data.unverified_contracts
        )
        agent_identity = self.identity_analyzer.score(
            has_metadata, metadata_fields, rep_count, rep_value, agents_sharing
        )

        result = self.engine.compute(
            longevity, activity, counterparty, contract_risk,
            agent_identity=agent_identity,
        )

        # Check for trust degradation
        existing = await self.db.get_score(agent_id)
        if existing:
            if self.alerts.should_alert(existing["trust_score"], result.trust_score):
                logger.warning(f"TrustDegraded: agent {agent_id} dropped {existing['trust_score']} -> {result.trust_score}")

        # Publish to chain + IPFS
        pub_result = await self.publisher.publish(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk, result.verdict
        )

        # Save to local cache
        await self.db.save_score(
            agent_id, wallet, result.trust_score,
            longevity, activity, counterparty, contract_risk,
            result.verdict, pub_result.get("feedback_txs", [""])[0],
            pub_result.get("evidence_uri", ""),
        )

        # Save graph edges
        for cp in data.counterparties:
            await self.db.save_edge(agent_id, cp, 1, False)

        logger.info(f"Scored agent {agent_id}: {result.trust_score} ({result.verdict}) [L={longevity} A={activity} C={counterparty} R={contract_risk} I={agent_identity}]")
        return result
