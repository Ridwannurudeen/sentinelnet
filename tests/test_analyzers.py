from agent.analyzers.longevity import LongevityAnalyzer


def test_longevity_new_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=0, first_tx_days_ago=0)
    assert score <= 20


def test_longevity_old_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=365, first_tx_days_ago=365)
    assert score >= 80


def test_longevity_medium_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=90, first_tx_days_ago=90)
    assert 20 <= score <= 30


def test_longevity_clamped():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=9999, first_tx_days_ago=9999)
    assert score == 100
