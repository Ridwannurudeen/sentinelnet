class ContractRiskAnalyzer:
    """Scores risk from contract interactions.

    Most contracts are unverified (not in our known list) — this is normal,
    not inherently risky. Only malicious contracts are heavily penalized.
    Contract diversity is a positive signal (DeFi participation).
    """

    def score(self, total_contracts: int, malicious_contracts: int,
              unverified_contracts: int) -> int:
        if total_contracts == 0:
            return 30  # No contract history = uncertain but not terrible

        # Malicious ratio is heavily penalized (60% weight)
        malicious_ratio = malicious_contracts / total_contracts
        malicious_score = (1.0 - malicious_ratio) * 100

        # Verified ratio as positive signal (20% weight)
        verified = total_contracts - unverified_contracts
        verified_ratio = verified / total_contracts if total_contracts > 0 else 0
        verified_score = verified_ratio * 100

        # Contract diversity as positive signal (20% weight)
        # More unique contracts = more DeFi participation
        diversity_score = min(total_contracts / 15, 1.0) * 100

        raw = malicious_score * 0.60 + verified_score * 0.20 + diversity_score * 0.20
        return min(round(raw), 100)
