import logging

logger = logging.getLogger(__name__)


class AgentIdentityAnalyzer:
    """Scores agent-level identity signals that differentiate agents even on shared wallets.

    Components:
    - Metadata completeness (40%): does tokenURI have description, endpoints, capabilities?
    - On-chain reputation (40%): has this agent received feedback from other clients?
    - Wallet exclusivity (20%): does this agent have a dedicated wallet or share with many?
    """

    def score(self, has_metadata: bool, metadata_fields: int,
              reputation_count: int, reputation_value: int,
              agents_sharing_wallet: int) -> int:
        # Metadata completeness (40% weight)
        if has_metadata:
            # More fields = more complete registration
            meta_score = min(metadata_fields / 5, 1.0) * 100
        else:
            meta_score = 0

        # On-chain reputation (40% weight)
        # Logarithmic: 1 feedback=30, 3=60, 10=85, 20+=100
        if reputation_count > 0:
            import math
            rep_score = min(math.log(reputation_count + 1) / math.log(21), 1.0) * 100
            # Adjust for sentiment: negative reputation pulls score down
            if reputation_value < 0:
                rep_score *= 0.3
            elif reputation_value == 0:
                rep_score *= 0.6
        else:
            rep_score = 15  # No reputation = unknown, slight base

        # Wallet exclusivity (20% weight)
        # 1 agent per wallet = 100, 2 = 70, 5 = 40, 10+ = 10
        if agents_sharing_wallet <= 1:
            exclusivity_score = 100
        elif agents_sharing_wallet <= 3:
            exclusivity_score = 70
        elif agents_sharing_wallet <= 10:
            exclusivity_score = 40
        else:
            exclusivity_score = 10

        raw = meta_score * 0.40 + rep_score * 0.40 + exclusivity_score * 0.20
        return min(round(raw), 100)
