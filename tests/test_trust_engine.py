from agent.trust_engine import TrustEngine, TrustResult


def test_compute_trust_score():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60, agent_identity=75)
    # 80*0.15 + 70*0.20 + 90*0.20 + 60*0.20 + 75*0.25 = 12 + 14 + 18 + 12 + 18.75 = 74.75 → 75
    assert result.trust_score == 75
    assert result.verdict == "TRUST"


def test_verdict_caution():
    engine = TrustEngine()
    result = engine.compute(longevity=50, activity=40, counterparty=50, contract_risk=40, agent_identity=50)
    # 50*0.15 + 40*0.20 + 50*0.20 + 40*0.20 + 50*0.25 = 7.5 + 8 + 10 + 8 + 12.5 = 46
    assert result.verdict == "CAUTION"


def test_verdict_reject():
    engine = TrustEngine()
    result = engine.compute(longevity=20, activity=10, counterparty=30, contract_risk=10, agent_identity=15)
    # 20*0.15 + 10*0.20 + 30*0.20 + 10*0.20 + 15*0.25 = 3 + 2 + 6 + 2 + 3.75 = 16.75 → 17
    assert result.verdict == "REJECT"


def test_compute_without_identity_defaults_zero():
    engine = TrustEngine()
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60)
    # agent_identity defaults to 0
    # 80*0.15 + 70*0.20 + 90*0.20 + 60*0.20 + 0*0.25 = 12 + 14 + 18 + 12 + 0 = 56
    assert result.trust_score == 56
    assert result.agent_identity == 0


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
    result = engine.compute(longevity=80, activity=70, counterparty=90, contract_risk=60,
                            agent_identity=75, sybil_risk=True)
    # 75 - 20 = 55
    assert result.trust_score == 55
    assert result.sybil_risk is True
