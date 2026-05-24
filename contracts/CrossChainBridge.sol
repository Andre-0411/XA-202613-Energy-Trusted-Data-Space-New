// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title CrossChainBridge
 * @notice 跨链桥合约 —— 支持跨链消息传递、资产锁定/释放和验证者管理
 * @dev 基于多签验证机制，确保跨链操作的安全性
 */
contract CrossChainBridge {
    /// @notice 跨链消息结构体
    struct CrossChainMessage {
        uint256 messageId;
        uint256 targetChainId;
        address sender;
        address targetContract;
        bytes data;
        uint256 timestamp;
        bool processed;
    }

    /// @notice 锁定资产记录
    struct LockedAsset {
        uint256 lockId;
        address owner;
        uint256 amount;
        uint256 targetChainId;
        bytes32 targetAddress;
        uint256 lockedAt;
        bool released;
    }

    /// @notice 验证者信息
    struct Validator {
        address addr;
        bool active;
        uint256 addedAt;
    }

    /// @notice 消息 ID → 消息信息
    mapping(uint256 => CrossChainMessage) private messages;

    /// @notice 锁定 ID → 锁定记录
    mapping(uint256 => LockedAsset) private lockedAssets;

    /// @notice 验证者地址 → 验证者信息
    mapping(address => Validator) private validators;

    /// @notice 验证者地址列表
    address[] private validatorList;

    /// @notice 消息 ID → 已签名的验证者地址集合
    mapping(uint256 => mapping(address => bool)) private messageSignatures;

    /// @notice 消息 ID → 签名数量
    mapping(uint256 => uint256) private signatureCount;

    /// @notice 自增计数器
    uint256 public nextMessageId;
    uint256 public nextLockId;

    /// @notice 合约拥有者
    address public owner;

    /// @notice 所需签名数量（多签阈值）
    uint256 public requiredSignatures;

    /// @notice 链 ID
    uint256 public chainId;

    // ==================== 事件 ====================

    /// @notice 跨链转账事件
    event CrossChainTransfer(uint256 indexed messageId, uint256 indexed targetChainId, address indexed sender, uint256 amount, uint256 timestamp);

    /// @notice 资产锁定事件
    event AssetLocked(uint256 indexed lockId, address indexed owner, uint256 amount, uint256 targetChainId, uint256 timestamp);

    /// @notice 资产释放事件
    event AssetReleased(uint256 indexed lockId, address indexed recipient, uint256 amount, uint256 timestamp);

    /// @notice 验证者添加事件
    event ValidatorAdded(address indexed validator, uint256 timestamp);

    /// @notice 验证者移除事件
    event ValidatorRemoved(address indexed validator, uint256 timestamp);

    /// @notice 消息验证签名事件
    event MessageSigned(uint256 indexed messageId, address indexed validator, uint256 currentSignatures, uint256 required);

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "CrossChainBridge: caller is not the owner");
        _;
    }

    modifier onlyValidator() {
        require(validators[msg.sender].active, "CrossChainBridge: caller is not an active validator");
        _;
    }

    modifier validMessage(uint256 _messageId) {
        require(messages[_messageId].messageId != 0, "CrossChainBridge: message does not exist");
        _;
    }

    modifier validLock(uint256 _lockId) {
        require(lockedAssets[_lockId].lockId != 0, "CrossChainBridge: lock does not exist");
        _;
    }

    // ==================== 构造函数 ====================

    constructor(uint256 _requiredSignatures) {
        require(_requiredSignatures > 0, "CrossChainBridge: invalid required signatures");
        owner = msg.sender;
        requiredSignatures = _requiredSignatures;
        chainId = block.chainid;
        nextMessageId = 1;
        nextLockId = 1;

        // 部署者默认为第一个验证者
        validators[msg.sender] = Validator({
            addr: msg.sender,
            active: true,
            addedAt: block.timestamp
        });
        validatorList.push(msg.sender);
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 发送跨链消息
     * @param _targetChainId 目标链 ID
     * @param _targetContract 目标合约地址
     * @param _data 消息数据
     * @return messageId 消息 ID
     */
    function sendCrossChainMessage(
        uint256 _targetChainId,
        address _targetContract,
        bytes calldata _data
    ) external payable returns (uint256 messageId) {
        require(_targetChainId != chainId, "CrossChainBridge: cannot send to same chain");
        require(_targetContract != address(0), "CrossChainBridge: invalid target contract");
        require(_data.length > 0, "CrossChainBridge: empty data");

        messageId = nextMessageId++;
        messages[messageId] = CrossChainMessage({
            messageId: messageId,
            targetChainId: _targetChainId,
            sender: msg.sender,
            targetContract: _targetContract,
            data: _data,
            timestamp: block.timestamp,
            processed: false
        });

        emit CrossChainTransfer(messageId, _targetChainId, msg.sender, msg.value, block.timestamp);
    }

    /**
     * @notice 锁定资产（用于跨链转移）
     * @param _targetChainId 目标链 ID
     * @param _targetAddress 目标链上的接收地址（bytes32）
     * @return lockId 锁定记录 ID
     */
    function lockAsset(uint256 _targetChainId, bytes32 _targetAddress) external payable returns (uint256 lockId) {
        require(msg.value > 0, "CrossChainBridge: amount must be positive");
        require(_targetAddress != bytes32(0), "CrossChainBridge: invalid target address");

        lockId = nextLockId++;
        lockedAssets[lockId] = LockedAsset({
            lockId: lockId,
            owner: msg.sender,
            amount: msg.value,
            targetChainId: _targetChainId,
            targetAddress: _targetAddress,
            lockedAt: block.timestamp,
            released: false
        });

        emit AssetLocked(lockId, msg.sender, msg.value, _targetChainId, block.timestamp);
    }

    /**
     * @notice 验证跨链消息签名（验证者调用）
     * @param _messageId 消息 ID
     */
    function signMessage(uint256 _messageId) external onlyValidator validMessage(_messageId) {
        require(!messageSignatures[_messageId][msg.sender], "CrossChainBridge: already signed");

        messageSignatures[_messageId][msg.sender] = true;
        signatureCount[_messageId]++;

        emit MessageSigned(_messageId, msg.sender, signatureCount[_messageId], requiredSignatures);
    }

    /**
     * @notice 处理已验证的跨链消息（达到签名阈值后调用）
     * @param _messageId 消息 ID
     */
    function processMessage(uint256 _messageId) external onlyValidator validMessage(_messageId) {
        CrossChainMessage storage msg_ = messages[_messageId];
        require(!msg_.processed, "CrossChainBridge: message already processed");
        require(signatureCount[_messageId] >= requiredSignatures, "CrossChainBridge: insufficient signatures");

        msg_.processed = true;

        // 调用目标合约
        (bool success, ) = msg_.targetContract.call(msg_.data);
        require(success, "CrossChainBridge: target call failed");
    }

    /**
     * @notice 释放锁定资产（接收方链上操作，由验证者触发）
     * @param _lockId 锁定记录 ID
     * @param _recipient 接收方地址
     */
    function releaseAsset(uint256 _lockId, address _recipient) external onlyValidator validLock(_lockId) {
        LockedAsset storage lock = lockedAssets[_lockId];
        require(!lock.released, "CrossChainBridge: already released");
        require(_recipient != address(0), "CrossChainBridge: invalid recipient");

        lock.released = true;

        (bool success, ) = payable(_recipient).call{value: lock.amount}("");
        require(success, "CrossChainBridge: transfer failed");

        emit AssetReleased(_lockId, _recipient, lock.amount, block.timestamp);
    }

    /**
     * @notice 添加验证者（仅合约拥有者）
     * @param _validator 验证者地址
     */
    function addValidator(address _validator) external onlyOwner {
        require(_validator != address(0), "CrossChainBridge: invalid address");
        require(!validators[_validator].active, "CrossChainBridge: already a validator");

        validators[_validator] = Validator({
            addr: _validator,
            active: true,
            addedAt: block.timestamp
        });
        validatorList.push(_validator);

        emit ValidatorAdded(_validator, block.timestamp);
    }

    /**
     * @notice 移除验证者（仅合约拥有者）
     * @param _validator 验证者地址
     */
    function removeValidator(address _validator) external onlyOwner {
        require(validators[_validator].active, "CrossChainBridge: not a validator");

        validators[_validator].active = false;

        emit ValidatorRemoved(_validator, block.timestamp);
    }

    /**
     * @notice 查询消息详情
     * @param _messageId 消息 ID
     * @return targetChainId 目标链 ID
     * @return sender 发送者
     * @return targetContract 目标合约
     * @return timestamp 时间戳
     * @return processed 是否已处理
     * @return signatures 已签名数量
     */
    function getMessage(uint256 _messageId)
        external
        view
        validMessage(_messageId)
        returns (
            uint256 targetChainId,
            address sender,
            address targetContract,
            uint256 timestamp,
            bool processed,
            uint256 signatures
        )
    {
        CrossChainMessage storage m = messages[_messageId];
        return (m.targetChainId, m.sender, m.targetContract, m.timestamp, m.processed, signatureCount[_messageId]);
    }

    /**
     * @notice 查询锁定资产详情
     * @param _lockId 锁定记录 ID
     * @return owner 资产拥有者
     * @return amount 锁定金额
     * @return targetChainId 目标链 ID
     * @return lockedAt 锁定时间
     * @return released 是否已释放
     */
    function getLockedAsset(uint256 _lockId)
        external
        view
        validLock(_lockId)
        returns (
            address owner_,
            uint256 amount,
            uint256 targetChainId,
            uint256 lockedAt,
            bool released
        )
    {
        LockedAsset storage l = lockedAssets[_lockId];
        return (l.owner, l.amount, l.targetChainId, l.lockedAt, l.released);
    }

    /**
     * @notice 查询当前验证者数量
     * @return count 活跃验证者数量
     */
    function getActiveValidatorCount() external view returns (uint256 count) {
        uint256 active = 0;
        for (uint256 i = 0; i < validatorList.length; i++) {
            if (validators[validatorList[i]].active) {
                active++;
            }
        }
        return active;
    }

    /**
     * @notice 查询是否为活跃验证者
     * @param _addr 地址
     * @return active 是否活跃
     */
    function isActiveValidator(address _addr) external view returns (bool active) {
        return validators[_addr].active;
    }

    /**
     * @notice 接收以太坊
     */
    receive() external payable {}
}
