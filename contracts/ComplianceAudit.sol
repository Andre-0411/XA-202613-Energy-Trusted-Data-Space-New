// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IComplianceAudit.sol";

/**
 * @title ComplianceAudit
 * @notice 合规审计合约 - 记录所有链上操作的不可篡改审计日志
 * @dev 实现 IComplianceAudit 接口，支持审计提交、审批/驳回流程
 */
contract ComplianceAudit is IComplianceAudit {
    /// @notice 合约管理员（审计管理者）
    address public admin;

    /// @notice 审计计数器
    uint256 private _auditCount;

    /// @notice auditId => 审计记录
    mapping(bytes32 => AuditRecord) private _audits;

    /// @notice targetId => auditId 列表
    mapping(string => bytes32[]) private _targetAudits;

    /// @notice 构造函数
    constructor() {
        admin = msg.sender;
    }

    /**
     * @notice 提交审计记录
     * @param auditType 审计类型（数据安全/隐私合规/操作规范/链上验证）
     * @param targetId 被审计对象标识
     * @param evidenceHash 存证哈希
     * @param result 审计结果（pass/fail/pending）
     * @param auditor 审计员标识
     * @return auditId 审计 ID（bytes32）
     */
    function submitAudit(
        string calldata auditType,
        string calldata targetId,
        bytes32 evidenceHash,
        string calldata result,
        string calldata auditor
    ) external override returns (bytes32) {
        require(bytes(auditType).length > 0, "Audit type required");
        require(bytes(targetId).length > 0, "Target ID required");
        require(bytes(auditor).length > 0, "Auditor required");

        bytes32 auditId = keccak256(
            abi.encodePacked(targetId, auditType, block.timestamp, msg.sender, _auditCount)
        );

        _audits[auditId] = AuditRecord({
            auditId: auditId,
            auditType: auditType,
            targetId: targetId,
            evidenceHash: evidenceHash,
            result: result,
            auditor: auditor,
            status: 0,  // 待审
            rejectReason: "",
            timestamp: block.timestamp
        });

        _targetAudits[targetId].push(auditId);
        _auditCount++;

        emit AuditSubmitted(auditId, auditType, targetId, block.timestamp);
        return auditId;
    }

    /**
     * @notice 批准审计（仅管理员）
     * @param auditId 审计 ID
     */
    function approveAudit(bytes32 auditId) external override {
        require(msg.sender == admin, "Only admin");
        require(_audits[auditId].auditId != bytes32(0), "Audit not found");
        require(_audits[auditId].status == 0, "Not in pending status");

        _audits[auditId].status = 1;  // 通过
        _audits[auditId].result = "pass";

        emit AuditApproved(auditId);
    }

    /**
     * @notice 驳回审计（仅管理员）
     * @param auditId 审计 ID
     * @param reason 驳回原因
     */
    function rejectAudit(bytes32 auditId, string calldata reason) external override {
        require(msg.sender == admin, "Only admin");
        require(_audits[auditId].auditId != bytes32(0), "Audit not found");
        require(_audits[auditId].status == 0, "Not in pending status");
        require(bytes(reason).length > 0, "Reason required");

        _audits[auditId].status = 2;  // 驳回
        _audits[auditId].result = "fail";
        _audits[auditId].rejectReason = reason;

        emit AuditRejected(auditId, reason);
    }

    /**
     * @notice 获取审计记录详情
     * @param auditId 审计 ID
     * @return 审计记录结构体
     */
    function getAudit(bytes32 auditId) external view override returns (AuditRecord memory) {
        require(_audits[auditId].auditId != bytes32(0), "Audit not found");
        return _audits[auditId];
    }

    /**
     * @notice 获取某目标的所有审计 ID
     * @param targetId 被审计对象标识
     * @return auditId 列表
     */
    function getAuditsByTarget(string calldata targetId) external view override returns (bytes32[] memory) {
        return _targetAudits[targetId];
    }

    /**
     * @notice 获取总审计记录数
     * @return 审计总数
     */
    function getAuditCount() external view override returns (uint256) {
        return _auditCount;
    }

    /**
     * @notice 转移管理员权限
     * @param newAdmin 新管理员地址
     */
    function transferAdmin(address newAdmin) external {
        require(msg.sender == admin, "Only admin");
        require(newAdmin != address(0), "Invalid address");
        admin = newAdmin;
    }
}
