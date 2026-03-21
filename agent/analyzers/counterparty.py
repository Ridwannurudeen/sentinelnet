class CounterpartyAnalyzer:
    """Scores the quality of an agent's interaction partners.

    Includes funding source analysis: CEX-funded wallets get a bonus
    (KYC'd origin), faucet-funded wallets get a penalty.
    """

    DIVERSITY_MAX = 30  # 30+ unique counterparties = max diversity bonus
    CEX_BONUS = 5       # +5 for CEX-funded (KYC'd origin)
    FAUCET_PENALTY = 3  # -3 for faucet-funded

    def score(self, total_counterparties: int, verified_counterparties: int,
              flagged_counterparties: int, funding_source: str = "unknown") -> int:
        if total_counterparties == 0:
            return 10  # No history = low trust

        # Clean ratio (60% weight) — what fraction is NOT flagged
        flagged_ratio = flagged_counterparties / total_counterparties
        clean_score = (1.0 - flagged_ratio) * 100

        # Verified ratio (25% weight) — what fraction is verified/known-good
        verified_ratio = verified_counterparties / total_counterparties
        verified_score = verified_ratio * 100

        # Diversity bonus (15% weight) — more unique counterparties = better
        diversity = min(total_counterparties / self.DIVERSITY_MAX, 1.0) * 100

        raw = clean_score * 0.60 + verified_score * 0.25 + diversity * 0.15

        # Funding source adjustment
        if funding_source == "cex":
            raw += self.CEX_BONUS
        elif funding_source == "faucet":
            raw -= self.FAUCET_PENALTY

        return max(0, min(round(raw), 100))
