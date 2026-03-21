from agent.analyzers.longevity import LongevityAnalyzer
from agent.analyzers.activity import ActivityAnalyzer
from agent.analyzers.counterparty import CounterpartyAnalyzer
from agent.analyzers.contract_risk import ContractRiskAnalyzer
from agent.analyzers.agent_identity import AgentIdentityAnalyzer


# --- Longevity (logarithmic curve) ---

def test_longevity_new_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=0, first_tx_days_ago=0)
    assert score == 0


def test_longevity_old_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=365, first_tx_days_ago=365)
    assert score >= 80


def test_longevity_medium_wallet():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=90, first_tx_days_ago=90)
    # Log curve: 15 * ln(91) ≈ 67
    assert 55 <= score <= 75


def test_longevity_clamped():
    analyzer = LongevityAnalyzer()
    score = analyzer.score(wallet_age_days=9999, first_tx_days_ago=9999)
    assert score == 100


# --- Activity (sqrt + balance) ---

def test_activity_no_transactions():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=0, active_days=0, total_days=30)
    assert score <= 10


def test_activity_high():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=500, active_days=200, total_days=365, eth_balance=1.0)
    assert score >= 75


def test_activity_moderate():
    analyzer = ActivityAnalyzer()
    score = analyzer.score(tx_count=50, active_days=30, total_days=90)
    assert 15 <= score <= 60


def test_activity_with_balance():
    analyzer = ActivityAnalyzer()
    # Same tx count but with ETH balance should score higher
    score_no_bal = analyzer.score(tx_count=100, active_days=30, total_days=90, eth_balance=0.0)
    score_with_bal = analyzer.score(tx_count=100, active_days=30, total_days=90, eth_balance=1.0)
    assert score_with_bal > score_no_bal


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
    assert score >= 75


def test_contract_risk_dangerous():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=10, malicious_contracts=5, unverified_contracts=3)
    assert 30 <= score <= 60


def test_contract_risk_moderate():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=20, malicious_contracts=1, unverified_contracts=5)
    # (1-0.05)*100*0.6 + (15/20)*100*0.2 + min(20/15,1)*100*0.2 = 57 + 15 + 20 = 92
    assert 80 <= score <= 95


def test_contract_risk_no_contracts():
    analyzer = ContractRiskAnalyzer()
    score = analyzer.score(total_contracts=0, malicious_contracts=0, unverified_contracts=0)
    assert score <= 30


# --- Agent Identity ---

def test_agent_identity_full_metadata():
    analyzer = AgentIdentityAnalyzer()
    score = analyzer.score(
        has_metadata=True, metadata_fields=5,
        reputation_count=10, reputation_value=100,
        agents_sharing_wallet=1,
    )
    assert score >= 75


def test_agent_identity_no_metadata_no_reputation():
    analyzer = AgentIdentityAnalyzer()
    score = analyzer.score(
        has_metadata=False, metadata_fields=0,
        reputation_count=0, reputation_value=0,
        agents_sharing_wallet=1,
    )
    assert score <= 30


def test_agent_identity_shared_wallet_penalty():
    analyzer = AgentIdentityAnalyzer()
    score_exclusive = analyzer.score(
        has_metadata=True, metadata_fields=3,
        reputation_count=5, reputation_value=50,
        agents_sharing_wallet=1,
    )
    score_shared = analyzer.score(
        has_metadata=True, metadata_fields=3,
        reputation_count=5, reputation_value=50,
        agents_sharing_wallet=20,
    )
    assert score_exclusive > score_shared


def test_agent_identity_negative_reputation():
    analyzer = AgentIdentityAnalyzer()
    score_positive = analyzer.score(
        has_metadata=True, metadata_fields=3,
        reputation_count=5, reputation_value=50,
        agents_sharing_wallet=1,
    )
    score_negative = analyzer.score(
        has_metadata=True, metadata_fields=3,
        reputation_count=5, reputation_value=-50,
        agents_sharing_wallet=1,
    )
    assert score_positive > score_negative
