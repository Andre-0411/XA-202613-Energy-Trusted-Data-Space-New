// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IAutoSettlement.sol";
import "./interfaces/IIdentityRegistry.sol";

/**
 * @title AutoSettlement
 * @notice 自动结算合约 - 数据交易的自动化结算和争议处理
 * @dev 实现 IAutoSettlement 接口，支持订阅式计费、自动结算和争议仲裁
 */
contract AutoSettlement is IAutoSettlement {
    /// @notice 身份注册中心
    IIdentityRegistry public identityRegistry;

    /// @notice 合约管理员（仲裁者）
    address public admin;

    /// @notice 结算 ID 计数器
    uint256 private _settlementIdCounter;

    /// @notice settlementId => 结算记录
    mapping(uint256 => SettlementRecord) private _settlements;

    /// @notice subscriptionId => settlementId 列表
    mapping(string => uint256[]) private _subscriptionSettlements;

    /// @notice planType => 费率（单位：wei/次 或 wei/周期）
    mapping(string => uint256) private _billingRules;

    /// @notice 事件：计费规则设置
    event BillingRuleSet(string planType, uint256 rate);

    /// @notice 构造函数
    /// @param _identityRegistry 身份注册中心地址
    constructor(address _identityRegistry) {
        identityRegistry = IIdentityRegistry(_identityRegistry);
        admin = msg.sender;
    }

    /**
     * @notice 创建结算单
     * @param subscriptionId 订阅 ID
     * @param amount 结算金额（wei）
     * @param billingPeriod 账期（如 "2024-01"）
     * @param payer 付款方地址
     * @param payee 收款方地址
     * @return settlementId 结算 ID
     */
    function createSettlement(
        string calldata subscriptionId,
        uint256 amount,
        string calldata billingPeriod,
        address payer,
        address payee
    ) external override returns (uint256) {
        require(bytes(subscriptionId).length > 0, "Subscription ID required");
        require(amount > 0, "Amount must be positive");
        require(payer != address(0) && payee != address(0), "Invalid address");

        _settlementIdCounter++;

        _settlements[_settlementIdCounter] = SettlementRecord({
            settlementId: _settlementIdCounter,
            subscriptionId: subscriptionId,
            amount: amount,
            billingPeriod: billingPeriod,
            payer: payer,
            payee: payee,
            status: 0,  // 待确认
            disputeReason: "",
            txHash: bytes32(0),
            createdAt: block.timestamp,
            confirmedAt: 0
        });

        _subscriptionSettlements[subscriptionId].push(_settlementIdCounter);

        emit SettlementCreated(_settlementIdCounter, subscriptionId, amount);
        return _settlementIdCounter;
    }

    /**
     * @notice 确认结算（付款方确认并完成付款）
     * @param settlementId 结算 ID
     */
    function confirmSettlement(uint256 settlementId) external override {
        SettlementRecord storage s = _settlements[settlementId];
        require(s.settlementId != 0, "Settlement not found");
        require(s.status == 0, "Not in pending status");
        require(msg.sender == s.payer || msg.sender == admin, "Not authorized");

        s.status = 1;  // 已确认
        s.confirmedAt = block.timestamp;
        s.txHash = keccak256(abi.encodePacked(settlementId, block.timestamp, msg.sender));

        emit SettlementConfirmed(settlementId, s.txHash);
    }

    /**
     * @notice 发起争议
     * @param settlementId 结算 ID
     * @param reason 争议原因
     */
    function disputeSettlement(uint256 settlementId, string calldata reason) external override {
        SettlementRecord storage s = _settlements[settlementId];
        require(s.settlementId != 0, "Settlement not found");
        require(s.status == 0, "Not in pending status");
        require(
            msg.sender == s.payer || msg.sender == s.payee,
            "Not authorized"
        );
        require(bytes(reason).length > 0, "Reason required");

        s.status = 2;  // 争议中
        s.disputeReason = reason;

        emit SettlementDisputed(settlementId, reason);
    }

    /**
     * @notice 解决争议（仅管理员/仲裁者）
     * @param settlementId 结算 ID
     * @param approve 是否批准（true=确认结算, false=取消结算）
     */
    function resolveDispute(uint256 settlementId, bool approve) external override {
        require(msg.sender == admin, "Only admin");
        SettlementRecord storage s = _settlements[settlementId];
        require(s.settlementId != 0, "Settlement not found");
        require(s.status == 2, "Not in dispute status");

        if (approve) {
            s.status = 3;  // 已解决（批准）
            s.confirmedAt = block.timestamp;
            s.txHash = keccak256(abi.encodePacked(settlementId, block.timestamp, "resolved"));
        } else {
            s.status = 4;  // 已取消
        }
    }

    /**
     * @notice 设置计费规则
     * @param planType 计费计划类型（如 "monthly", "per_call", "volume"）
     * @param rate 费率（wei）
     */
    function setBillingRule(string calldata planType, uint256 rate) external override {
        require(msg.sender == admin, "Only admin");
        require(bytes(planType).length > 0, "Plan type required");

        _billingRules[planType] = rate;
        emit BillingRuleSet(planType, rate);
    }

    /**
     * @notice 获取结算详情
     * @param settlementId 结算 ID
     * @return 结算记录结构体
     */
    function getSettlement(uint256 settlementId) external view override returns (SettlementRecord memory) {
        require(_settlements[settlementId].settlementId != 0, "Settlement not found");
        return _settlements[settlementId];
    }

    /**
     * @notice 获取某订阅的所有结算记录 ID
     * @param subscriptionId 订阅 ID
     * @return settlementId 列表
     */
    function getSettlementsBySubscription(string calldata subscriptionId) external view override returns (uint256[] memory) {
        return _subscriptionSettlements[subscriptionId];
    }

    /**
     * @notice 获取计费规则
     * @param planType 计费计划类型
     * @return rate 费率
     */
    function getBillingRule(string calldata planType) external view returns (uint256) {
        return _billingRules[planType];
    }
}
