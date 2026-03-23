// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SentinelNetStaking {
    struct Stake {
        uint256 agentId;
        uint8 score;
        uint256 amount;
        uint256 stakedAt;
        bool challenged;
        bool resolved;
        bool challengeSucceeded;
        address challenger;
    }

    address public sentinel;
    uint256 public challengeWindow = 72 hours;
    mapping(bytes32 => Stake) public stakes;
    bool private _locked;

    event ScoreStaked(uint256 indexed agentId, uint8 score, uint256 amount, bytes32 stakeId);
    event StakeChallenged(bytes32 indexed stakeId, address challenger);
    event ChallengeResolved(bytes32 indexed stakeId, bool succeeded, address challenger);
    event TrustDegraded(uint256 indexed agentId, uint8 previousScore, uint8 newScore, uint256 timestamp);

    modifier nonReentrant() {
        require(!_locked, "Reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    constructor(address _sentinel) {
        sentinel = _sentinel;
    }

    function stakeScore(uint256 agentId, uint8 score) external payable {
        require(msg.sender == sentinel, "Only sentinel");
        require(msg.value > 0, "Must stake ETH");
        bytes32 stakeId = keccak256(abi.encodePacked(agentId, score, block.timestamp));
        stakes[stakeId] = Stake(agentId, score, msg.value, block.timestamp, false, false, false, address(0));
        emit ScoreStaked(agentId, score, msg.value, stakeId);
    }

    function challenge(bytes32 stakeId) external {
        Stake storage s = stakes[stakeId];
        require(s.amount > 0, "No stake");
        require(!s.challenged, "Already challenged");
        require(block.timestamp <= s.stakedAt + challengeWindow, "Window closed");
        s.challenged = true;
        s.challenger = msg.sender;
        emit StakeChallenged(stakeId, msg.sender);
    }

    function resolveChallenge(bytes32 stakeId, bool _challengeSucceeded) external nonReentrant {
        require(msg.sender == sentinel, "Only sentinel");
        Stake storage s = stakes[stakeId];
        require(s.challenged, "Not challenged");
        require(!s.resolved, "Already resolved");
        s.resolved = true;
        s.challengeSucceeded = _challengeSucceeded;

        if (_challengeSucceeded) {
            // Slash: send staked ETH to the challenger as reward
            uint256 amount = s.amount;
            s.amount = 0;
            (bool success, ) = payable(s.challenger).call{value: amount}("");
            require(success, "Slash transfer failed");
        }
        emit ChallengeResolved(stakeId, _challengeSucceeded, s.challenger);
    }

    function withdraw(bytes32 stakeId) external nonReentrant {
        require(msg.sender == sentinel, "Only sentinel");
        Stake storage s = stakes[stakeId];
        require(s.amount > 0, "No stake");
        require(block.timestamp > s.stakedAt + challengeWindow, "Window open");
        // Only allow withdraw if unchallenged, or challenge was resolved in sentinel's favor
        require(!s.challenged || (s.resolved && !s.challengeSucceeded), "Challenge pending or lost");
        uint256 amount = s.amount;
        s.amount = 0;
        (bool success, ) = payable(sentinel).call{value: amount}("");
        require(success, "Transfer failed");
    }

    function emitTrustDegraded(uint256 agentId, uint8 prev, uint8 next) external {
        require(msg.sender == sentinel, "Only sentinel");
        emit TrustDegraded(agentId, prev, next, block.timestamp);
    }
}
