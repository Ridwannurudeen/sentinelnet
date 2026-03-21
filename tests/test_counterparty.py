from agent.analyzers.counterparty import CounterpartyAnalyzer


def test_basic_score():
    a = CounterpartyAnalyzer()
    score = a.score(20, 5, 1)
    assert 0 < score <= 100


def test_no_counterparties():
    a = CounterpartyAnalyzer()
    assert a.score(0, 0, 0) == 10


def test_all_verified():
    a = CounterpartyAnalyzer()
    score = a.score(30, 30, 0)
    assert score >= 80


def test_all_flagged():
    a = CounterpartyAnalyzer()
    score = a.score(30, 0, 30)
    assert score < 30


def test_cex_funding_bonus():
    """CEX-funded wallets get +5 bonus."""
    a = CounterpartyAnalyzer()
    score_unknown = a.score(20, 5, 0, funding_source="unknown")
    score_cex = a.score(20, 5, 0, funding_source="cex")
    assert score_cex == score_unknown + 5


def test_faucet_funding_penalty():
    """Faucet-funded wallets get -3 penalty."""
    a = CounterpartyAnalyzer()
    score_unknown = a.score(20, 5, 0, funding_source="unknown")
    score_faucet = a.score(20, 5, 0, funding_source="faucet")
    assert score_faucet == score_unknown - 3


def test_eoa_funding_neutral():
    """EOA funding source has no adjustment."""
    a = CounterpartyAnalyzer()
    score_unknown = a.score(20, 5, 0, funding_source="unknown")
    score_eoa = a.score(20, 5, 0, funding_source="eoa")
    assert score_eoa == score_unknown


def test_score_clamped_to_100():
    """Score can't exceed 100 even with CEX bonus."""
    a = CounterpartyAnalyzer()
    score = a.score(50, 50, 0, funding_source="cex")
    assert score <= 100


def test_score_minimum_zero():
    """Score can't go below 0 even with faucet penalty."""
    a = CounterpartyAnalyzer()
    # Very bad: all flagged + faucet
    score = a.score(30, 0, 30, funding_source="faucet")
    assert score >= 0
