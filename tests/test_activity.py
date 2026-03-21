import time
from agent.analyzers.activity import ActivityAnalyzer


def test_basic_score():
    a = ActivityAnalyzer()
    score = a.score(100, 20, 60, eth_balance=0.5)
    assert 0 < score <= 100


def test_zero_activity():
    a = ActivityAnalyzer()
    assert a.score(0, 0, 0) == 0


def test_high_activity():
    a = ActivityAnalyzer()
    score = a.score(500, 60, 100, eth_balance=5.0)
    assert score >= 80


def test_burst_penalty_applied():
    """If >80% of txs are in a single 24h window, penalty applies."""
    a = ActivityAnalyzer()
    base_ts = int(time.time()) - 86400 * 30
    # 20 txs all in one hour
    burst_timestamps = [base_ts + i * 60 for i in range(20)]
    score_burst = a.score(20, 1, 30, eth_balance=0.1, tx_timestamps=burst_timestamps)
    # Same tx count but spread across 30 days
    spread_timestamps = [base_ts + i * 86400 for i in range(20)]
    score_spread = a.score(20, 20, 30, eth_balance=0.1, tx_timestamps=spread_timestamps)
    assert score_burst < score_spread


def test_no_burst_penalty_when_spread():
    """No penalty when txs are evenly distributed."""
    a = ActivityAnalyzer()
    base_ts = int(time.time()) - 86400 * 60
    # 30 txs spread across 30 days
    timestamps = [base_ts + i * 86400 * 2 for i in range(30)]
    score = a.score(30, 30, 60, eth_balance=0.1, tx_timestamps=timestamps)
    # With burst it would be score - 15, so check it's reasonable
    assert score > 30


def test_no_burst_penalty_few_txs():
    """Burst detection doesn't fire with < 5 txs."""
    a = ActivityAnalyzer()
    base_ts = int(time.time())
    timestamps = [base_ts + i for i in range(3)]
    score_with = a.score(3, 1, 30, eth_balance=0.1, tx_timestamps=timestamps)
    score_without = a.score(3, 1, 30, eth_balance=0.1, tx_timestamps=None)
    assert score_with == score_without


def test_burst_penalty_value():
    """Verify the actual penalty amount."""
    a = ActivityAnalyzer()
    assert a.BURST_PENALTY == 15
    base_ts = int(time.time())
    # All 10 txs in one minute
    timestamps = [base_ts + i for i in range(10)]
    penalty = a._burst_penalty(timestamps)
    assert penalty == 15


def test_no_burst_penalty_below_threshold():
    """70% clustering shouldn't trigger the 80% threshold."""
    a = ActivityAnalyzer()
    base_ts = int(time.time())
    # 7 txs in one hour, 3 txs spread across weeks
    timestamps = [base_ts + i * 60 for i in range(7)]
    timestamps += [base_ts + 86400 * (i + 1) * 5 for i in range(3)]
    penalty = a._burst_penalty(timestamps)
    assert penalty == 0
