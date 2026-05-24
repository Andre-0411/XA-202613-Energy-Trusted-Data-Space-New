// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IComplianceAudit {
    struct AuditRecord {
        bytes32 auditId;
        string auditType;     // 数据安全/隐私合规/操作规范/链上验证
        string targetId;
        bytes32 evidenceHash;
        string result;        // pass/fail/pending
        string auditor;
        uint8 status;         // 0:待审, 1:通过, 2:驳回
        string rejectReason;
        uint256 timestamp;
    }

    event AuditSubmitted(bytes32 auditId, string auditType, string targetId, uint256 timestamp);
    event AuditApproved(bytes32 auditId);
    event AuditRejected(bytes32 auditId, string reason);

    function submitAudit(string calldata auditType, string calldata targetId, bytes32 evidenceHash, string calldata result, string calldata auditor) external returns (bytes32);
    function approveAudit(bytes32 auditId) external;
    function rejectAudit(bytes32 auditId, string calldata reason) external;
    function getAudit(bytes32 auditId) external view returns (AuditRecord memory);
    function getAuditsByTarget(string calldata targetId) external view returns (bytes32[] memory);
    function getAuditCount() external view returns (uint256);
}
