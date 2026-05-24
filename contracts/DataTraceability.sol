// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title DataTraceability
 * @notice 溯源追踪合约 —— 记录数据来源、流转链路和操作日志
 * @dev 支持链上存证，确保数据全生命周期可追溯
 */
contract DataTraceability {
    /// @notice 操作类型枚举
    enum OperationType { Created, Accessed, Transferred, Modified, Deleted, Shared }

    /// @notice 来源记录结构体
    struct OriginRecord {
        uint256 recordId;
        uint256 assetId;
        address recorder;
        string source;          // 数据来源描述
        string datasetHash;     // 数据集哈希
        uint256 recordedAt;
        bool exists;
    }

    /// @notice 流转记录结构体
    struct TransferRecord {
        uint256 transferId;
        uint256 assetId;
        address from;
        address to;
        string description;
        uint256 transferredAt;
    }

    /// @notice 操作日志结构体
    struct OperationLog {
        uint256 logId;
        uint256 assetId;
        address operator;
        OperationType opType;
        string detail;
        uint256 timestamp;
    }

    /// @notice 来源记录 ID → 来源记录
    mapping(uint256 => OriginRecord) private originRecords;

    /// @notice 资产 ID → 流转记录列表
    mapping(uint256 => TransferRecord[]) private assetTransfers;

    /// @notice 资产 ID → 操作日志列表
    mapping(uint256 => OperationLog[]) private assetLogs;

    /// @notice 资产 ID → 来源记录 ID
    mapping(uint256 => uint256) private assetOrigin;

    /// @notice 自增计数器
    uint256 public nextRecordId;
    uint256 public nextTransferId;
    uint256 public nextLogId;

    /// @notice 合约拥有者
    address public owner;

    // ==================== 事件 ====================

    /// @notice 数据来源记录事件
    event DataOriginRecorded(uint256 indexed recordId, uint256 indexed assetId, address indexed recorder, string source, uint256 timestamp);

    /// @notice 数据流转事件
    event DataTransferred(uint256 indexed transferId, uint256 indexed assetId, address indexed from, address to, uint256 timestamp);

    /// @notice 操作日志事件
    event OperationLogged(uint256 indexed logId, uint256 indexed assetId, address indexed operator, OperationType opType, uint256 timestamp);

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "DataTraceability: caller is not the owner");
        _;
    }

    // ==================== 构造函数 ====================

    constructor() {
        owner = msg.sender;
        nextRecordId = 1;
        nextTransferId = 1;
        nextLogId = 1;
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 记录数据来源
     * @param _assetId 资产 ID
     * @param _source 数据来源描述
     * @param _datasetHash 数据集哈希
     * @return recordId 来源记录 ID
     */
    function recordOrigin(uint256 _assetId, string calldata _source, string calldata _datasetHash) external returns (uint256 recordId) {
        require(_source.length > 0, "DataTraceability: source cannot be empty");

        recordId = nextRecordId++;
        originRecords[recordId] = OriginRecord({
            recordId: recordId,
            assetId: _assetId,
            recorder: msg.sender,
            source: _source,
            datasetHash: _datasetHash,
            recordedAt: block.timestamp,
            exists: true
        });

        // 首次记录设置为资产来源
        if (assetOrigin[_assetId] == 0) {
            assetOrigin[_assetId] = recordId;
        }

        // 自动记录操作日志
        _logOperation(_assetId, OperationType.Created, string.concat("Origin: ", _source));

        emit DataOriginRecorded(recordId, _assetId, msg.sender, _source, block.timestamp);
    }

    /**
     * @notice 记录数据流转
     * @param _assetId 资产 ID
     * @param _to 接收方地址
     * @param _description 流转描述
     * @return transferId 流转记录 ID
     */
    function recordTransfer(uint256 _assetId, address _to, string calldata _description) external returns (uint256 transferId) {
        require(_to != address(0), "DataTraceability: invalid recipient");

        transferId = nextTransferId++;
        TransferRecord memory record = TransferRecord({
            transferId: transferId,
            assetId: _assetId,
            from: msg.sender,
            to: _to,
            description: _description,
            transferredAt: block.timestamp
        });

        assetTransfers[_assetId].push(record);
        _logOperation(_assetId, OperationType.Transferred, string.concat("Transfer to: ", _to.toHexString()));

        emit DataTransferred(transferId, _assetId, msg.sender, _to, block.timestamp);
    }

    /**
     * @notice 记录操作日志
     * @param _assetId 资产 ID
     * @param _opType 操作类型
     * @param _detail 操作详情
     * @return logId 日志 ID
     */
    function logOperation(uint256 _assetId, OperationType _opType, string calldata _detail) external returns (uint256 logId) {
        logId = nextLogId++;
        assetLogs[_assetId].push(OperationLog({
            logId: logId,
            assetId: _assetId,
            operator: msg.sender,
            opType: _opType,
            detail: _detail,
            timestamp: block.timestamp
        }));

        emit OperationLogged(logId, _assetId, msg.sender, _opType, block.timestamp);
    }

    /**
     * @notice 查询资产来源记录
     * @param _assetId 资产 ID
     * @return recordId 来源记录 ID
     * @return source 数据来源
     * @return datasetHash 数据集哈希
     * @return recorder 记录者
     * @return recordedAt 记录时间
     */
    function getAssetOrigin(uint256 _assetId)
        external
        view
        returns (
            uint256 recordId,
            string memory source,
            string memory datasetHash,
            address recorder,
            uint256 recordedAt
        )
    {
        uint256 rid = assetOrigin[_assetId];
        require(rid != 0, "DataTraceability: no origin record");

        OriginRecord storage r = originRecords[rid];
        return (r.recordId, r.source, r.datasetHash, r.recorder, r.recordedAt);
    }

    /**
     * @notice 查询资产的流转历史
     * @param _assetId 资产 ID
     * @return transfers 流转记录数组
     */
    function getTransferHistory(uint256 _assetId) external view returns (TransferRecord[] memory transfers) {
        return assetTransfers[_assetId];
    }

    /**
     * @notice 查询资产的操作日志
     * @param _assetId 资产 ID
     * @return logs 操作日志数组
     */
    function getOperationLogs(uint256 _assetId) external view returns (OperationLog[] memory logs) {
        return assetLogs[_assetId];
    }

    /**
     * @notice 查询资产的流转次数
     * @param _assetId 资产 ID
     * @return count 流转次数
     */
    function getTransferCount(uint256 _assetId) external view returns (uint256 count) {
        return assetTransfers[_assetId].length;
    }

    // ==================== 内部函数 ====================

    /**
     * @notice 内部记录操作日志
     */
    function _logOperation(uint256 _assetId, OperationType _opType, string memory _detail) internal {
        uint256 logId = nextLogId++;
        assetLogs[_assetId].push(OperationLog({
            logId: logId,
            assetId: _assetId,
            operator: msg.sender,
            opType: _opType,
            detail: _detail,
            timestamp: block.timestamp
        }));

        emit OperationLogged(logId, _assetId, msg.sender, _opType, block.timestamp);
    }
}
