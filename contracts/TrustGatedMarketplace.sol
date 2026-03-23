// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title TrustGatedMarketplace — Integration proof: agent marketplace gated by SentinelNet
/// @notice Demonstrates how any contract can use TrustGate to only allow trusted agents.
///         Agents must pass the SentinelNet trust check before listing or executing services.

interface ITrustGate {
    function isTrusted(uint256 agentId) external view returns (bool);
    function getTrustScore(uint256 agentId) external view returns (uint8);
    function getVerdict(uint256 agentId) external view returns (string memory);
}

contract TrustGatedMarketplace {
    ITrustGate public trustGate;
    address public owner;
    bool private _locked;

    struct ServiceListing {
        uint256 agentId;
        address provider;
        string description;
        uint256 price;
        bool active;
    }

    mapping(uint256 => ServiceListing) public listings;
    uint256 public listingCount;

    event ServiceListed(uint256 indexed listingId, uint256 indexed agentId, string description, uint256 price);
    event ServiceExecuted(uint256 indexed listingId, uint256 indexed agentId, address indexed buyer);
    event AgentRejected(uint256 indexed agentId, string reason);

    error AgentNotTrusted(uint256 agentId);
    error ListingNotActive(uint256 listingId);
    error InsufficientPayment();

    modifier onlyTrustedAgent(uint256 agentId) {
        if (!trustGate.isTrusted(agentId)) {
            emit AgentRejected(agentId, "SentinelNet: agent not trusted");
            revert AgentNotTrusted(agentId);
        }
        _;
    }

    modifier nonReentrant() {
        require(!_locked, "Reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    constructor(address _trustGate) {
        trustGate = ITrustGate(_trustGate);
        owner = msg.sender;
    }

    /// @notice List a service. Only trusted agents can list.
    function listService(
        uint256 agentId,
        string calldata description,
        uint256 price
    ) external onlyTrustedAgent(agentId) returns (uint256 listingId) {
        listingId = listingCount++;
        listings[listingId] = ServiceListing({
            agentId: agentId,
            provider: msg.sender,
            description: description,
            price: price,
            active: true
        });
        emit ServiceListed(listingId, agentId, description, price);
    }

    /// @notice Execute a service. The providing agent must still be trusted at execution time.
    function executeService(uint256 listingId) external payable nonReentrant {
        ServiceListing storage listing = listings[listingId];
        if (!listing.active) revert ListingNotActive(listingId);
        if (msg.value < listing.price) revert InsufficientPayment();

        // Re-check trust at execution time — trust can change
        if (!trustGate.isTrusted(listing.agentId)) {
            emit AgentRejected(listing.agentId, "SentinelNet: agent trust revoked since listing");
            revert AgentNotTrusted(listing.agentId);
        }

        // Pay the provider
        (bool sent, ) = payable(listing.provider).call{value: listing.price}("");
        require(sent, "Payment failed");

        // Refund excess
        if (msg.value > listing.price) {
            (bool refunded, ) = payable(msg.sender).call{value: msg.value - listing.price}("");
            require(refunded, "Refund failed");
        }

        emit ServiceExecuted(listingId, listing.agentId, msg.sender);
    }

    /// @notice Check if an agent can participate in the marketplace
    function canParticipate(uint256 agentId) external view returns (bool trusted, uint8 score, string memory verdict) {
        trusted = trustGate.isTrusted(agentId);
        score = trustGate.getTrustScore(agentId);
        verdict = trustGate.getVerdict(agentId);
    }

    /// @notice Deactivate a listing
    function deactivateListing(uint256 listingId) external {
        require(listings[listingId].provider == msg.sender || msg.sender == owner, "Not authorized");
        listings[listingId].active = false;
    }
}
