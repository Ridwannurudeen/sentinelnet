from typing import Dict, Set, List

MIN_CLUSTER_SIZE = 3
MAX_EXTERNAL_RATIO = 0.2  # If >80% of interactions are within cluster -> sybil
MIN_WALLET_SHARING = 3    # 3+ agents sharing a wallet = sybil signal


class SybilDetector:
    def detect(self, edges: Dict[int, Set[str]],
               wallet_to_agent: Dict[str, int] = None,
               wallet_agent_count: Dict[str, List[int]] = None) -> List[List[int]]:
        if wallet_to_agent is None:
            wallet_to_agent = {}

        clusters = []
        seen = set()

        # Method 1: Wallet-sharing detection
        # Multiple agent IDs mapped to the same wallet = sybil signal
        if wallet_agent_count:
            for wallet, agent_ids in wallet_agent_count.items():
                if len(agent_ids) >= MIN_WALLET_SHARING:
                    cluster = sorted(agent_ids)
                    clusters.append(cluster)
                    seen.update(cluster)

        # Method 2: Interaction graph clique detection (original)
        agent_ids = [a for a in edges.keys() if a not in seen]
        if len(agent_ids) >= MIN_CLUSTER_SIZE:
            agent_graph: Dict[int, Set[int]] = {a: set() for a in agent_ids}
            for agent_id, counterparties in edges.items():
                if agent_id in seen:
                    continue
                for cp in counterparties:
                    if cp in wallet_to_agent:
                        other = wallet_to_agent[cp]
                        if other != agent_id and other not in seen:
                            agent_graph.setdefault(agent_id, set()).add(other)

            visited = set()
            for agent_id in agent_ids:
                if agent_id in visited:
                    continue
                cluster = self._expand_cluster(agent_id, agent_graph, edges, wallet_to_agent)
                if len(cluster) >= MIN_CLUSTER_SIZE:
                    clusters.append(sorted(cluster))
                    visited.update(cluster)

        return clusters

    def _expand_cluster(self, start: int, agent_graph: Dict[int, Set[int]],
                        edges: Dict[int, Set[str]],
                        wallet_to_agent: Dict[str, int]) -> List[int]:
        cluster = {start}
        candidates = agent_graph.get(start, set())
        for candidate in candidates:
            candidate_peers = agent_graph.get(candidate, set())
            if cluster.issubset(candidate_peers | {candidate}):
                cluster.add(candidate)

        # Verify cluster is isolated — most interactions are internal
        for member in list(cluster):
            total = len(edges.get(member, set()))
            internal = len(agent_graph.get(member, set()) & cluster)
            if total > 0 and internal / total < (1 - MAX_EXTERNAL_RATIO):
                cluster.discard(member)

        return list(cluster)
