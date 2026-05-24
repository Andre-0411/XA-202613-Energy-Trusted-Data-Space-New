// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

/**
 * @title EvidenceStore
 * @dev 专用存证存储合约
 *
 * 提供完整的存证生命周期管理，包括:
 * - 存证提交与存储
 * - 批量存证提交
 * - 存证验证
 * - 存证溯源
 * - 时间戳证明
 * 与 IdentityRegistry 和 UsageLogger 集成
 */
contract EvidenceStore {
    // ==================== 状态变量 ====================

    /// @notice IdentityRegistry 合约地址
    address public identityRegistry;

    /// @notice UsageLogger 合约地址
    address public usageLogger;

    /// @notice 合约所有者
    address public owner;

    /// @notice 存证记录总数
    uint256 public totalEvidence;

    // ==================== 数据结构 ====================

    /// @notice 存证记录
    struct Evidence {
        string evidenceId;        // 存证 ID
        string resourceType;      // 资源类型
        string resourceId;        // 资源 ID
        string nodeType;          // 节点类型 (8 节点证据链)
        bytes32 dataHash;         // 数据 SM3 哈希
        bytes evidenceData;       // 存证数据
        string submitterDid;      // 提交者 DID
        uint256 blockNumber;      // 区块高度
        uint256 timestamp;        // 时间戳
        bool isValid;             // 是否有效
    }

    /// @notice 存证 ID => Evidence
    mapping(string => Evidence) private evidences;

    /// @notice 存证 ID 是否已存在
    mapping(string => bool) private evidenceExists;

    /// @notice 资源 ID => 存证 ID 列表
    mapping(string => string[]) private resourceEvidences;

    /// @notice 提交者 DID => 存证 ID 列表
    mapping(string => string[]) private submitterEvidences;

    // ==================== 事件 ====================

    /// @notice 事件：存证提交
    event EvidenceSubmitted(
        string indexed evidenceId,
        string indexed resourceId,
        string nodeType,
        string submitterDid,
        bytes32 dataHash,
        uint256 timestamp
    );

    /// @notice 事件：批量存证提交
    event BatchEvidenceSubmitted(
        uint256 count,
        string submitterDid,
        uint256 timestamp
    );

    /// @notice 事件：存证失效
    event EvidenceInvalidated(
        string indexed evidenceId,
        uint256 timestamp
    );

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "EvidenceStore: caller is not the owner");
        _;
    }

    modifier evidencePresent(string memory evidenceId) {
        require(evidenceExists[evidenceId], "EvidenceStore: evidence not found");
        _;
    }

    // ==================== 构造函数 ====================

    /**
     * @dev 构造函数
     * @param _identityRegistry IdentityRegistry 合约地址
     * @param _usageLogger UsageLogger 合约地址
     */
    constructor(address _identityRegistry, address _usageLogger) {
        require(_identityRegistry != address(0), "EvidenceStore: invalid identity registry");
        require(_usageLogger != address(0), "EvidenceStore: invalid usage logger");
        identityRegistry = _identityRegistry;
        usageLogger = _usageLogger;
        owner = msg.sender;
    }

    // ==================== 外部函数 ====================

    /**
     * @dev 提交单条存证
     * @param evidenceId 存证 ID
     * @param resourceType 资源类型
     * @param resourceId 资源 ID
     * @param nodeType 节点类型
     * @param dataHash 数据 SM3 哈希 (bytes32)
     * @param evidenceData 存证数据
     * @param submitterDid 提交者 DID
     */
    function submitEvidence(
        string memory evidenceId,
        string memory resourceType,
        string memory resourceId,
        string memory nodeType,
        bytes32 dataHash,
        bytes memory evidenceData,
        string memory submitterDid
    ) external {
        require(bytes(evidenceId).length > 0, "EvidenceStore: empty evidenceId");
        require(!evidenceExists[evidenceId], "EvidenceStore: already exists");
        require(dataHash != bytes32(0), "EvidenceStore: empty dataHash");

        evidences[evidenceId] = Evidence({
            evidenceId: evidenceId,
            resourceType: resourceType,
            resourceId: resourceId,
            nodeType: nodeType,
            dataHash: dataHash,
            evidenceData: evidenceData,
            submitterDid: submitterDid,
            blockNumber: block.number,
            timestamp: block.timestamp,
            isValid: true
        });

        evidenceExists[evidenceId] = true;
        resourceEvidences[resourceId].push(evidenceId);
        submitterEvidences[submitterDid].push(evidenceId);
        totalEvidence++;

        emit EvidenceSubmitted(
            evidenceId, resourceId, nodeType, submitterDid, dataHash, block.timestamp
        );
    }

    /**
     * @dev 批量提交存证
     * @param evidenceIds 存证 ID 列表
     * @param resourceTypes 资源类型列表
     * @param resourceIds 资源 ID 列表
     * @param nodeTypes 节点类型列表
     * @param dataHashes 数据哈希列表
     * @param evidenceDataList 存证数据列表
     * @param submitterDid 提交者 DID
     */
    function batchSubmitEvidence(
        string[] memory evidenceIds,
        string[] memory resourceTypes,
        string[] memory resourceIds,
        string[] memory nodeTypes,
        bytes32[] memory dataHashes,
        bytes[] memory evidenceDataList,
        string memory submitterDid
    ) external {
        uint256 count = evidenceIds.length;
        require(count > 0, "EvidenceStore: empty batch");
        require(
            count == resourceTypes.length &&
            count == resourceIds.length &&
            count == nodeTypes.length &&
            count == dataHashes.length &&
            count == evidenceDataList.length,
            "EvidenceStore: array length mismatch"
        );

        for (uint256 i = 0; i < count; i++) {
            require(!evidenceExists[evidenceIds[i]], "EvidenceStore: evidence already exists");
            require(dataHashes[i] != bytes32(0), "EvidenceStore: empty dataHash");

            evidences[evidenceIds[i]] = Evidence({
                evidenceId: evidenceIds[i],
                resourceType: resourceTypes[i],
                resourceId: resourceIds[i],
                nodeType: nodeTypes[i],
                dataHash: dataHashes[i],
                evidenceData: evidenceDataList[i],
                submitterDid: submitterDid,
                blockNumber: block.number,
                timestamp: block.timestamp,
                isValid: true
            });

            evidenceExists[evidenceIds[i]] = true;
            resourceEvidences[resourceIds[i]].push(evidenceIds[i]);
            submitterEvidences[submitterDid].push(evidenceIds[i]);
            totalEvidence++;
        }

        emit BatchEvidenceSubmitted(count, submitterDid, block.timestamp);
    }

    /**
     * @dev 验证存证
     * @param evidenceId 存证 ID
     * @param dataHash 验证用的数据哈希
     * @return isValid 存证是否有效且哈希匹配
     */
    function verifyEvidence(
        string memory evidenceId,
        bytes32 dataHash
    ) external view evidencePresent(evidenceId) returns (bool isValid) {
        Evidence storage ev = evidences[evidenceId];
        return ev.isValid && ev.dataHash == dataHash;
    }

    /**
     * @dev 使存证失效
     * @param evidenceId 存证 ID
     */
    function invalidateEvidence(string memory evidenceId) external evidencePresent(evidenceId) {
        require(msg.sender == owner, "EvidenceStore: not authorized");
        evidences[evidenceId].isValid = false;
        emit EvidenceInvalidated(evidenceId, block.timestamp);
    }

    // ==================== 视图函数 ====================

    /**
     * @dev 获取存证详情
     * @param evidenceId 存证 ID
     * @return evidence 存证记录
     */
    function getEvidence(string memory evidenceId) external view evidencePresent(evidenceId) returns (
        Evidence memory evidence
    ) {
        return evidences[evidenceId];
    }

    /**
     * @dev 获取资源的存证 ID 列表
     * @param resourceId 资源 ID
     * @return evidenceIds 存证 ID 列表
     */
    function getEvidenceByResource(string memory resourceId) external view returns (string[] memory evidenceIds) {
        return resourceEvidences[resourceId];
    }

    /**
     * @dev 获取提交者的存证 ID 列表
     * @param submitterDid 提交者 DID
     * @return evidenceIds 存证 ID 列表
     */
    function getEvidenceBySubmitter(string memory submitterDid) external view returns (string[] memory evidenceIds) {
        return submitterEvidences[submitterDid];
    }

    /**
     * @dev 检查存证是否存在
     * @param evidenceId 存证 ID
     * @return 存在与否
     */
    function hasEvidence(string memory evidenceId) external view returns (bool) {
        return evidenceExists[evidenceId];
    }
}
