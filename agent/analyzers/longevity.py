import math


class LongevityAnalyzer:
    """Scores wallet age using logarithmic curve.

    Logarithmic scaling gives meaningful differentiation across ranges:
    7 days → ~25, 30 days → ~45, 90 days → ~60, 180 days → ~72, 365 days → ~83, 730+ → ~95
    """

    def score(self, wallet_age_days: int, first_tx_days_ago: int) -> int:
        age = max(wallet_age_days, first_tx_days_ago)
        if age <= 0:
            return 0
        # Logarithmic curve: score = 15 * ln(age + 1), capped at 100
        raw = 15 * math.log(age + 1)
        return min(round(raw), 100)
