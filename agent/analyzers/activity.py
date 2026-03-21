import math


class ActivityAnalyzer:
    """Scores transaction frequency, consistency, and economic weight.

    Uses sqrt scaling for tx count (diminishing returns) and adds
    balance component for skin-in-the-game signal.
    """

    TX_COUNT_MAX = 500     # 500+ txs = max contribution
    CONSISTENCY_MAX = 0.6  # active 60%+ of days = max contribution

    def score(self, tx_count: int, active_days: int, total_days: int,
              eth_balance: float = 0.0) -> int:
        if total_days == 0 and tx_count == 0:
            return 0

        # Volume component (40% weight) — sqrt scaling for diminishing returns
        volume = min(math.sqrt(tx_count) / math.sqrt(self.TX_COUNT_MAX), 1.0)

        # Consistency component (30% weight) — active_days / total_days
        if total_days > 0:
            consistency_ratio = active_days / total_days
            consistency = min(consistency_ratio / self.CONSISTENCY_MAX, 1.0)
        else:
            consistency = 0

        # Balance component (30% weight) — ETH balance as skin in the game
        # 0.01 ETH = ~30, 0.1 ETH = ~60, 1 ETH = ~90, 5+ ETH = 100
        if eth_balance > 0:
            balance_score = min(math.log10(eth_balance * 100 + 1) / math.log10(501), 1.0)
        else:
            balance_score = 0

        raw = (volume * 0.40 + consistency * 0.30 + balance_score * 0.30) * 100
        return min(round(raw), 100)
