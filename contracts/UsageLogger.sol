// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IUsageLogger.sol";
import "./interfaces/IIdentityRegistry.sol";

/**
 * @title UsageLogger
 * @notice 使用日志合约 - 基于链式哈希记录数据资产的每次使用操作
 * @dev 实现 IUsageLogger 接口，支持证据链式存储和完整性验证
 */
contract UsageLogger is IUsageLogger {
    /// @notice 身份注册中心
    IIdentityRegistry public identityRegistry;

    /// @notice 合约管理员
    address public admin;

    /// @notice 记录计数器
    uint256 private _recordCount;

    /// @notice recordId => 使用记录
    mapping(bytes32 => UsageRecord) private _records;

    /// @notice resourceId => recordId 列表
    mapping(string => bytes32[]) private _resourceRecords;

    /// @notice 上一条记录的哈希（用于链式哈希）
    bytes32 private _lastHash;

    /// @notice 构造函数
    /// @param _identityRegistry 身份注册中心地址
    constructor(address _identityRegistry) {
        identityRegistry = IIdentityRegistry(_identityRegistry);
        admin = msg.sender;
        _lastHash = bytes32(0);
    }

    /**
     * @notice 记录使用日志
     * @param nodeType 节点类型（collect/preprocess/classify/publish/apply/compute/result/settle）
     * @param resourceId 资源标识
     * @param resourceType 资源类型
     * @param dataHash 数据哈希
     * @param evidenceData 存证原始数据
     * @return recordId 记录 ID（bytes32）
     */
    function logUsage(
        string calldata nodeType,
        string calldata resourceId,
        string calldata resourceType,
        bytes32 dataHash,
        bytes calldata evidenceData
    ) external override returns (bytes32) {
        require(bytes(nodeType).length > 0, "Node type required");
        require(bytes(resourceId).length > 0, "Resource ID required");

        // 生成 recordId: keccak256(abi.encodePacked(resourceId, nodeType, block.timestamp, msg.sender, _recordCount))
        bytes32 recordId = keccak256(
            abi.encodePacked(resourceId, nodeType, block.timestamp, msg.sender, _recordCount)
        );

        _records[recordId] = UsageRecord({
            recordId: recordId,
            nodeType: nodeType,
            resourceId: resourceId,
            resourceType: resourceType,
            dataHash: dataHash,
            evidenceData: evidenceData,
            prevHash: _lastHash,
            operator: msg.sender,
            timestamp: block.timestamp,
            isValid: true
        });

        _resourceRecords[resourceId].push(recordId);
        _lastHash = recordId;
        _recordCount++;

        emit UsageLogged(recordId, nodeType, resourceId, dataHash, _lastHash, block.timestamp);
        return recordId;
    }

    /**
     * @notice 验证记录是否存在且有效
     * @param recordId 记录 ID
     * @return 是否有效
     */
    function verifyRecord(bytes32 recordId) external view override returns (bool) {
        return _records[recordId].isValid;
    }

    /**
     * @notice 获取记录详情
     * @param recordId 记录 ID
     * @return 记录结构体
     */
    function getRecord(bytes32 recordId) external view override returns (UsageRecord memory) {
        require(_records[recordId].isValid, "Record not found");
        return _records[recordId];
    }

    /**
     * @notice 获取某资源的所有记录 ID
     * @param resourceId 资源标识
     * @return recordId 列表
     */
    function getRecordsByResource(string calldata resourceId) external view override returns (bytes32[] memory) {
        return _resourceRecords[resourceId];
    }

    /**
     * @notice 获取总记录数
     * @return 记录总数
     */
    function getRecordCount() external view override returns (uint256) {
        return _recordCount;
    }

    /**
     * @notice 获取最后一条记录的哈希
     * @return 最后记录哈希
     */
    function getLastHash() external view override returns (bytes32) {
        return _lastHash;
    }
}
