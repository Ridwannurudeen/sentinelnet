class ContractRiskAnalyzer:
    """Scores risk from contract interactions."""

    def score(self, total_contracts: int, malicious_contracts: int,
              unverified_contracts: int) -> int:
        if total_contracts == 0:
            return 20  # No contract history = uncertain

        # Malicious ratio is heavily penalized (70% weight)
        malicious_ratio = malicious_contracts / total_contracts
        malicious_score = (1.0 - malicious_ratio) * 100

        # Unverified ratio is moderately penalized (30% weight)
        unverified_ratio = unverified_contracts / total_contracts
        unverified_score = (1.0 - unverified_ratio) * 100

        raw = malicious_score * 0.70 + unverified_score * 0.30
        return min(round(raw), 100)
