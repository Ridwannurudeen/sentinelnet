// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title SentinelNet TrustGate — Composable on-chain trust oracle for ERC-8004 agents
/// @notice Other contracts inherit TrustGate to gate execution by agent trust score.
///         Scores are updated by the SentinelNet sentinel from off-chain analysis.
/// @dev Designed to be imported by any contract on Base that needs trust-gated agent interactions.
///
/// Usage:
///   import {TrustGate} from "sentinelnet/TrustGate.sol";
///   contract MyMarketplace is TrustGate(sentinelAddr) {
///       function execute(uint256 agentId) external onlyTrusted(agentId) { ... }
///   }

contract TrustGate {
    struct TrustRecord {
        uint8 score;
        uint8 verdict;  // 0=UNSCORED, 1=TRUST, 2=CAUTION, 3=REJECT
        uint40 updatedAt;
        string evidenceURI;
    }

    address public sentinel;
    uint8 public trustThreshold = 55;   // >= 55 = TRUST
    uint8 public cautionThreshold = 40; // >= 40 = CAUTION, < 40 = REJECT

    mapping(uint256 => TrustRecord) public trustRecords;
    uint256 public totalScored;
    uint256[] private _scoredAgents;

    event TrustUpdated(uint256 indexed agentId, uint8 score, uint8 verdict, string evidenceURI);
    event ThresholdUpdated(uint8 trustThreshold, uint8 cautionThreshold);
    event SentinelTransferred(address indexed previousSentinel, address indexed newSentinel);

    error AgentNotTrusted(uint256 agentId, uint8 score, uint8 verdict);
    error AgentNotScored(uint256 agentId);
    error OnlySentinel();

    modifier onlySentinel() {
        if (msg.sender != sentinel) revert OnlySentinel();
        _;
    }

    modifier onlyTrusted(uint256 agentId) {
        TrustRecord storage r = trustRecords[agentId];
        if (r.updatedAt == 0) revert AgentNotScored(agentId);
        if (r.verdict != 1) revert AgentNotTrusted(agentId, r.score, r.verdict);
        _;
    }

    modifier onlyNotRejected(uint256 agentId) {
        TrustRecord storage r = trustRecords[agentId];
        if (r.updatedAt > 0 && r.verdict == 3) revert AgentNotTrusted(agentId, r.score, r.verdict);
        _;
    }

    constructor(address _sentinel) {
        sentinel = _sentinel;
    }

    /// @notice Update trust score for an agent. Called by SentinelNet after analysis.
    function updateTrust(
        uint256 agentId,
        uint8 score,
        string calldata evidenceURI
    ) external onlySentinel {
        uint8 verdict;
        if (score >= trustThreshold) {
            verdict = 1; // TRUST
        } else if (score >= cautionThreshold) {
            verdict = 2; // CAUTION
        } else {
            verdict = 3; // REJECT
        }

        if (trustRecords[agentId].updatedAt == 0) {
            totalScored++;
            _scoredAgents.push(agentId);
        }

        trustRecords[agentId] = TrustRecord({
            score: score,
            verdict: verdict,
            updatedAt: uint40(block.timestamp),
            evidenceURI: evidenceURI
        });

        emit TrustUpdated(agentId, score, verdict, evidenceURI);
    }

    /// @notice Batch update trust scores for multiple agents.
    function batchUpdateTrust(
        uint256[] calldata agentIds,
        uint8[] calldata scores,
        string[] calldata evidenceURIs
    ) external onlySentinel {
        require(agentIds.length == scores.length && scores.length == evidenceURIs.length, "Length mismatch");
        for (uint256 i = 0; i < agentIds.length; i++) {
            uint8 verdict;
            if (scores[i] >= trustThreshold) {
                verdict = 1;
            } else if (scores[i] >= cautionThreshold) {
                verdict = 2;
            } else {
                verdict = 3;
            }
            if (trustRecords[agentIds[i]].updatedAt == 0) {
                totalScored++;
                _scoredAgents.push(agentIds[i]);
            }
            trustRecords[agentIds[i]] = TrustRecord({
                score: scores[i],
                verdict: verdict,
                updatedAt: uint40(block.timestamp),
                evidenceURI: evidenceURIs[i]
            });
            emit TrustUpdated(agentIds[i], scores[i], verdict, evidenceURIs[i]);
        }
    }

    // ─── View Functions (for other contracts to query) ───

    /// @notice Check if an agent is trusted. Returns true if verdict == TRUST.
    function isTrusted(uint256 agentId) external view returns (bool) {
        return trustRecords[agentId].verdict == 1;
    }

    /// @notice Get the trust score for an agent (0-100).
    function getTrustScore(uint256 agentId) external view returns (uint8) {
        return trustRecords[agentId].score;
    }

    /// @notice Get the full trust record for an agent.
    function getTrustRecord(uint256 agentId) external view returns (
        uint8 score, uint8 verdict, uint40 updatedAt, string memory evidenceURI
    ) {
        TrustRecord storage r = trustRecords[agentId];
        return (r.score, r.verdict, r.updatedAt, r.evidenceURI);
    }

    /// @notice Get verdict as string.
    function getVerdict(uint256 agentId) external view returns (string memory) {
        uint8 v = trustRecords[agentId].verdict;
        if (v == 1) return "TRUST";
        if (v == 2) return "CAUTION";
        if (v == 3) return "REJECT";
        return "UNSCORED";
    }

    // ─── Admin Functions ───

    function updateThresholds(uint8 _trust, uint8 _caution) external onlySentinel {
        require(_trust > _caution, "Trust must be above caution");
        trustThreshold = _trust;
        cautionThreshold = _caution;
        emit ThresholdUpdated(_trust, _caution);
    }

    function transferSentinel(address newSentinel) external onlySentinel {
        require(newSentinel != address(0), "Zero address");
        emit SentinelTransferred(sentinel, newSentinel);
        sentinel = newSentinel;
    }
}
