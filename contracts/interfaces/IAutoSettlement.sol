// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAutoSettlement {
    struct SettlementRecord {
        uint256 settlementId;
        string subscriptionId;
        uint256 amount;
        string billingPeriod;
        address payer;
        address payee;
        uint8 status;         // 0:待确认, 1:已确认, 2:争议中, 3:已解决, 4:已取消
        string disputeReason;
        bytes32 txHash;
        uint256 createdAt;
        uint256 confirmedAt;
    }

    event SettlementCreated(uint256 settlementId, string subscriptionId, uint256 amount);
    event SettlementConfirmed(uint256 settlementId, bytes32 txHash);
    event SettlementDisputed(uint256 settlementId, string reason);

    function createSettlement(string calldata subscriptionId, uint256 amount, string calldata billingPeriod, address payer, address payee) external returns (uint256);
    function confirmSettlement(uint256 settlementId) external;
    function disputeSettlement(uint256 settlementId, string calldata reason) external;
    function resolveDispute(uint256 settlementId, bool approve) external;
    function setBillingRule(string calldata planType, uint256 rate) external;
    function getSettlement(uint256 settlementId) external view returns (SettlementRecord memory);
    function getSettlementsBySubscription(string calldata subscriptionId) external view returns (uint256[] memory);
}
