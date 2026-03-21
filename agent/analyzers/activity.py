import math
from typing import List


class ActivityAnalyzer:
    """Scores transaction frequency, consistency, and economic weight.

    Uses sqrt scaling for tx count (diminishing returns) and adds
    balance component for skin-in-the-game signal.
    Applies burst penalty if >80% of txs cluster in a 24h window.
    """

    TX_COUNT_MAX = 500     # 500+ txs = max contribution
    CONSISTENCY_MAX = 0.6  # active 60%+ of days = max contribution
    BURST_THRESHOLD = 0.80  # >80% of txs in one 24h window = bot signal
    BURST_PENALTY = 15      # points deducted for burst activity

    def score(self, tx_count: int, active_days: int, total_days: int,
              eth_balance: float = 0.0, tx_timestamps: List[int] = None) -> int:
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

        # Burst penalty — if most txs cluster in a single 24h window
        penalty = self._burst_penalty(tx_timestamps) if tx_timestamps else 0

        return max(0, min(round(raw) - penalty, 100))

    def _burst_penalty(self, timestamps: List[int]) -> int:
        """Penalize if >80% of transactions fall within a single 24-hour window."""
        if not timestamps or len(timestamps) < 5:
            return 0
        sorted_ts = sorted(timestamps)
        n = len(sorted_ts)
        window = 86400  # 24 hours
        max_in_window = 0
        j = 0
        for i in range(n):
            while j < n and sorted_ts[j] - sorted_ts[i] <= window:
                j += 1
            max_in_window = max(max_in_window, j - i)
        ratio = max_in_window / n
        if ratio >= self.BURST_THRESHOLD:
            return self.BURST_PENALTY
        return 0
