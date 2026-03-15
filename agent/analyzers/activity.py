class ActivityAnalyzer:
    """Scores transaction frequency and consistency."""

    TX_COUNT_MAX = 500     # 500+ txs = max contribution
    CONSISTENCY_MAX = 0.6  # active 60%+ of days = max contribution

    def score(self, tx_count: int, active_days: int, total_days: int) -> int:
        if total_days == 0:
            return 0

        # Volume component (60% weight)
        volume = min(tx_count / self.TX_COUNT_MAX, 1.0)

        # Consistency component (40% weight) — active_days / total_days
        consistency_ratio = active_days / total_days
        consistency = min(consistency_ratio / self.CONSISTENCY_MAX, 1.0)

        raw = (volume * 0.6 + consistency * 0.4) * 100
        return min(round(raw), 100)
