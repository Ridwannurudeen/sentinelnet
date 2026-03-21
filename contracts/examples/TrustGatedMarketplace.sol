// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {TrustGate} from "../TrustGate.sol";

/// @title TrustGated Agent Marketplace — Example integration of SentinelNet TrustGate
/// @notice Demonstrates how any contract on Base can gate agent interactions by trust score.
/// @dev This is a reference implementation showing the TrustGate pattern.

contract TrustGatedMarketplace is TrustGate {
    struct Service {
        uint256 agentId;
        string name;
        uint256 price;
        bool active;
    }

    mapping(uint256 => Service) public services;
    uint256 public serviceCount;

    event ServiceListed(uint256 indexed agentId, uint256 serviceId, string name, uint256 price);
    event ServiceRequested(uint256 indexed agentId, uint256 serviceId);
    event ServiceDeactivated(uint256 serviceId);

    /// @notice List a service — only TRUSTED agents can list.
    /// @dev Uses the onlyTrusted modifier from TrustGate.
    function listService(
        uint256 agentId,
        string calldata name,
        uint256 price
    ) external onlyTrusted(agentId) {
        serviceCount++;
        services[serviceCount] = Service({
            agentId: agentId,
            name: name,
            price: price,
            active: true
        });
        emit ServiceListed(agentId, serviceCount, name, price);
    }

    /// @notice Request a service — rejected agents are blocked, caution agents allowed.
    /// @dev Uses onlyNotRejected: allows TRUST + CAUTION, blocks REJECT.
    function requestService(
        uint256 requesterAgentId,
        uint256 serviceId
    ) external onlyNotRejected(requesterAgentId) {
        Service storage svc = services[serviceId];
        require(svc.active, "Service inactive");
        emit ServiceRequested(requesterAgentId, serviceId);
    }

    /// @notice Check if an agent can use this marketplace.
    function canInteract(uint256 agentId) external view returns (bool trusted, string memory verdict) {
        trusted = this.isTrusted(agentId);
        verdict = this.getVerdict(agentId);
    }
}
