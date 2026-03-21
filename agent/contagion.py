"""Trust Contagion Engine — PageRank-style recursive trust propagation.

When an agent interacts with REJECT agents, trust degrades proportionally.
When an agent interacts with TRUST agents, a small boost is applied.
Propagation is iterative and converges after a few rounds.
"""
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

CONTAGION_DAMPING = 0.3       # How much neighbor trust affects you (0=none, 1=full)
NEGATIVE_WEIGHT = 0.6         # Weight for negative contagion (interacting with REJECT)
POSITIVE_WEIGHT = 0.2         # Weight for positive contagion (interacting with TRUST)
MAX_ITERATIONS = 3            # Convergence rounds
CONVERGENCE_THRESHOLD = 0.5   # Stop if max adjustment < this


class ContagionEngine:
    """Propagates trust through the agent interaction graph."""

    def compute_adjustments(self, scores: Dict[int, dict],
                            edges: List[dict]) -> Dict[int, int]:
        """Compute trust adjustments for all agents based on their neighbors.

        Args:
            scores: {agent_id: {"trust_score": int, "verdict": str, "wallet": str}}
            edges: [{"agent_id": int, "counterparty": str, "interaction_count": int}]

        Returns:
            {agent_id: adjustment} — positive or negative integer adjustments.
        """
        if not scores or not edges:
            return {}

        # Build wallet → agent_id lookup
        wallet_to_agents: Dict[str, List[int]] = {}
        for aid, s in scores.items():
            w = s.get("wallet", "").lower()
            if w:
                wallet_to_agents.setdefault(w, []).append(aid)

        # Build agent → neighbor scores graph
        agent_neighbors: Dict[int, List[Tuple[int, int]]] = {}  # agent → [(neighbor_score, weight)]
        for edge in edges:
            aid = edge["agent_id"]
            cp_wallet = edge["counterparty"].lower()
            count = edge.get("interaction_count", 1)

            # Find which agents own this counterparty wallet
            neighbor_agents = wallet_to_agents.get(cp_wallet, [])
            for neighbor_id in neighbor_agents:
                if neighbor_id == aid:
                    continue
                neighbor_score = scores.get(neighbor_id, {}).get("trust_score", 50)
                agent_neighbors.setdefault(aid, []).append((neighbor_score, count))

        # Iterative propagation
        adjustments: Dict[int, float] = {aid: 0.0 for aid in scores}

        for iteration in range(MAX_ITERATIONS):
            new_adjustments: Dict[int, float] = {}
            max_change = 0.0

            for aid in scores:
                neighbors = agent_neighbors.get(aid, [])
                if not neighbors:
                    new_adjustments[aid] = adjustments[aid]
                    continue

                # Weighted average of neighbor influence
                total_weight = sum(w for _, w in neighbors)
                if total_weight == 0:
                    new_adjustments[aid] = adjustments[aid]
                    continue

                contagion = 0.0
                for neighbor_score, weight in neighbors:
                    normalized_weight = weight / total_weight
                    # Negative contagion: interacting with low-trust agents pulls you down
                    if neighbor_score < 40:
                        penalty = (40 - neighbor_score) / 40 * NEGATIVE_WEIGHT
                        contagion -= penalty * normalized_weight * 100
                    # Positive contagion: interacting with high-trust agents gives small boost
                    elif neighbor_score >= 55:
                        boost = (neighbor_score - 55) / 45 * POSITIVE_WEIGHT
                        contagion += boost * normalized_weight * 100

                new_adj = contagion * CONTAGION_DAMPING
                change = abs(new_adj - adjustments.get(aid, 0))
                max_change = max(max_change, change)
                new_adjustments[aid] = new_adj

            adjustments = new_adjustments
            if max_change < CONVERGENCE_THRESHOLD:
                logger.info(f"Contagion converged after {iteration + 1} iterations")
                break

        # Round and filter insignificant adjustments
        result = {}
        for aid, adj in adjustments.items():
            rounded = round(adj)
            if rounded != 0:
                result[aid] = max(-15, min(10, rounded))  # Cap: -15 to +10

        if result:
            logger.info(f"Contagion adjustments: {len(result)} agents affected "
                        f"(avg={sum(result.values())/len(result):.1f})")
        return result
