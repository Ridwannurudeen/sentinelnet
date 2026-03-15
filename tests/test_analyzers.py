from agent.analyzers.longevity import LongevityAnalyzer
from agent.analyzers.activity import ActivityAnalyzer
from agent.analyzers.counterparty import CounterpartyAnalyzer
from agent.analyzers.contract_risk import ContractRiskAnalyzer


# --- Longevity ---

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


# --- Activity ---

def test_activity_no_transactions():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=0, active_days=0, total_days=30)
    assert score <= 10


def test_activity_high():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=500, active_days=200, total_days=365)
    assert score >= 75


def test_activity_moderate():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=50, active_days=30, total_days=90)
    assert 20 <= score <= 75


def test_activity_clamped():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=99999, active_days=365, total_days=365)
    assert score == 100


# --- Counterparty ---

def test_counterparty_all_clean():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=50, verified_counterparties=45, flagged_counterparties=0)
    assert score >= 85


def test_counterparty_all_flagged():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=10, verified_counterparties=0, flagged_counterparties=10)
    assert score <= 10


def test_counterparty_mixed():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=20, verified_counterparties=10, flagged_counterparties=3)
    assert 40 <= score <= 75


def test_counterparty_no_interactions():
    analyzer = CounterpartyAnalyzer()
    score = analyzer.score(total_counterparties=0, verified_counterparties=0, flagged_counterparties=0)
    assert score <= 20


# --- Contract Risk ---

def test_contract_risk_clean():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=30, malicious_contracts=0, unverified_contracts=2)
    assert score >= 85


def test_contract_risk_dangerous():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=10, malicious_contracts=5, unverified_contracts=3)
    # (1-0.5)*100*0.7 + (1-0.3)*100*0.3 = 35 + 21 = 56
    assert 50 <= score <= 60


def test_contract_risk_moderate():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=20, malicious_contracts=1, unverified_contracts=5)
    # (1-0.05)*100*0.7 + (1-0.25)*100*0.3 = 66.5 + 22.5 = 89
    assert 85 <= score <= 95


def test_contract_risk_no_contracts():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=0, malicious_contracts=0, unverified_contracts=0)
    assert score <= 30
