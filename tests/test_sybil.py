from agent.sybil import SybilDetector


def test_no_sybil_diverse_interactions():
    detector = SybilDetector()
    edges = {
        1: {"0xa", "0xb", "0xc", "0xd", "0xe"},
        2: {"0xa", "0xf", "0xg", "0xh"},
    }
    clusters = detector.detect(edges)
    assert len(clusters) == 0


def test_sybil_ring_detected():
    detector = SybilDetector()
    # Agents 1, 2, 3 only interact with each other
    edges = {
        1: {"wallet_2", "wallet_3"},
        2: {"wallet_1", "wallet_3"},
        3: {"wallet_1", "wallet_2"},
    }
    wallet_to_agent = {"wallet_1": 1, "wallet_2": 2, "wallet_3": 3}
    clusters = detector.detect(edges, wallet_to_agent)
    assert len(clusters) == 1
    assert set(clusters[0]) == {1, 2, 3}


def test_sybil_needs_minimum_cluster_size():
    detector = SybilDetector()
    # Only 2 agents — below minimum cluster size of 3
    edges = {
        1: {"wallet_2"},
        2: {"wallet_1"},
    }
    wallet_to_agent = {"wallet_1": 1, "wallet_2": 2}
    clusters = detector.detect(edges, wallet_to_agent)
    assert len(clusters) == 0
