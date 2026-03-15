from agent.trust_engine import TrustEngine, TrustResult


def test_compute_trust_score():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60)
    # 80*0.20 + 70*0.25 + 90*0.30 + 60*0.25 = 16 + 17.5 + 27 + 15 = 75.5 → 76
    assert result.trust_score == 76
    assert result.verdict == "TRUST"


def test_verdict_caution():
    engine = TrustEngine()
    result = engine.compute(longevity=50, activity=40, counterparty=50, contract_risk=40)
    # 50*0.20 + 40*0.25 + 50*0.30 + 40*0.25 = 10 + 10 + 15 + 10 = 45
    assert result.verdict == "CAUTION"


def test_verdict_reject():
    engine = TrustEngine()
    result = engine.compute(longevity=20, activity=10, counterparty=30, contract_risk=10)
    # 20*0.20 + 10*0.25 + 30*0.30 + 10*0.25 = 4 + 2.5 + 9 + 2.5 = 18
    assert result.verdict == "REJECT"


def test_decay_recent_score_unchanged():
    engine = TrustEngine()
    effective = engine.apply_decay(base_score=90, days_since_scored=0)
    assert effective == 90


def test_decay_30_days():
    engine = TrustEngine()
    effective = engine.apply_decay(base_score=90, days_since_scored=30)
    # 90 * e^(-0.01*30) = 90 * 0.7408 ≈ 67
    assert 65 <= effective <= 69


def test_decay_stale_flag():
    engine = TrustEngine()
    assert engine.is_stale(days_since_scored=0) is False
    assert engine.is_stale(days_since_scored=7) is True


def test_sybil_penalty():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60, sybil_risk=True)
    # 76 - 20 = 56
    assert result.trust_score == 56
    assert result.sybil_risk is True
