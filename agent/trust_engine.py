import math
from dataclasses import dataclass

WEIGHTS = {
    "longevity": 0.20,
    "activity": 0.25,
    "counterparty": 0.30,
    "contract_risk": 0.25,
}

DECAY_LAMBDA = 0.01
STALE_THRESHOLD_DAYS = 7
SYBIL_PENALTY = 20


@dataclass
class TrustResult:
    trust_score: int
    verdict: str
    longevity: int
    activity: int
    counterparty: int
    contract_risk: int
    sybil_risk: bool = False
    decay_applied: bool = False


class TrustEngine:
    def compute(self, longevity: int, activity: int, counterparty: int,
                contract_risk: int, sybil_risk: bool = False) -> TrustResult:
        raw = (
            longevity * WEIGHTS["longevity"]
            + activity * WEIGHTS["activity"]
            + counterparty * WEIGHTS["counterparty"]
            + contract_risk * WEIGHTS["contract_risk"]
        )
        score = round(raw)
        if sybil_risk:
            score = max(0, score - SYBIL_PENALTY)
        verdict = self._verdict(score)
        return TrustResult(
            trust_score=score,
            verdict=verdict,
            longevity=longevity,
            activity=activity,
            counterparty=counterparty,
            contract_risk=contract_risk,
            sybil_risk=sybil_risk,
        )

    def apply_decay(self, base_score: int, days_since_scored: float) -> int:
        decayed = base_score * math.exp(-DECAY_LAMBDA * days_since_scored)
        return round(decayed)

    def is_stale(self, days_since_scored: float) -> bool:
        return days_since_scored >= STALE_THRESHOLD_DAYS

    def _verdict(self, score: int) -> str:
        if score >= 70:
            return "TRUST"
        elif score >= 40:
            return "CAUTION"
        return "REJECT"
