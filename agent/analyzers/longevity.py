class LongevityAnalyzer:
    """Scores wallet age. Older wallets = more trustworthy."""

    MAX_AGE_DAYS = 365  # 1 year = max score

    def score(self, wallet_age_days: int, first_tx_days_ago: int) -> int:
        age = max(wallet_age_days, first_tx_days_ago)
        raw = min(age / self.MAX_AGE_DAYS, 1.0) * 100
        return min(round(raw), 100)
