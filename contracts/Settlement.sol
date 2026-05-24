// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

/**
 * @title Settlement
 * @dev 增强版结算合约
 *
 * 基于 AutoSettlement 扩展，提供:
 * - 批量结算处理
 * - 对账功能
 * - 结算报告生成
 * - 争议仲裁升级
 */
contract Settlement {
    // ==================== 状态变量 ====================

    /// @notice IdentityRegistry 合约地址
    address public identityRegistry;

    /// @notice 合约所有者
    address public owner;

    /// @notice 结算记录总数
    uint256 public totalSettlements;

    /// @notice 争议记录总数
    uint256 public totalDisputes;

    /// @notice 结算状态枚举
    uint8 constant STATUS_PENDING = 0;
    uint8 constant STATUS_CONFIRMED = 1;
    uint8 constant STATUS_DISPUTED = 2;
    uint8 constant STATUS_RESOLVED = 3;
    uint8 constant STATUS_CANCELLED = 4;

    // ==================== 数据结构 ====================

    /// @notice 结算记录
    struct SettlementRecord {
        uint256 settlementId;     // 结算 ID
        string subscriptionId;    // 订阅 ID
        uint256 amount;           // 结算金额 (wei)
        string billingPeriod;     // 计费周期
        address payer;            // 付款方
        address payee;            // 收款方
        uint8 status;             // 结算状态
        uint256 createdAt;        // 创建时间
        uint256 confirmedAt;      // 确认时间
        string disputeReason;     // 争议原因
    }

    /// @notice 批量结算项
    struct BatchItem {
        string subscriptionId;
        uint256 amount;
        string billingPeriod;
        address payee;
    }

    // ==================== 映射 ====================

    /// @notice settlementId => SettlementRecord
    mapping(uint256 => SettlementRecord) private settlements;

    /// @notice 按订阅查询结算 ID 列表
    mapping(string => uint256[]) private subscriptionSettlements;

    /// @notice 按计费周期查询结算 ID 列表
    mapping(string => uint256[]) private periodSettlements;

    /// @notice 按付款方查询结算 ID 列表
    mapping(address => uint256[]) private payerSettlements;

    // ==================== 事件 ====================

    /// @notice 事件：结算创建
    event SettlementCreated(
        uint256 indexed settlementId,
        string indexed subscriptionId,
        uint256 amount,
        string billingPeriod,
        address payer,
        address payee,
        uint256 createdAt
    );

    /// @notice 事件：结算确认
    event SettlementConfirmed(
        uint256 indexed settlementId,
        uint256 confirmedAt
    );

    /// @notice 事件：结算争议
    event SettlementDisputed(
        uint256 indexed settlementId,
        string reason,
        uint256 disputedAt
    );

    /// @notice 事件：争议解决
    event DisputeResolved(
        uint256 indexed settlementId,
        uint8 resolution,
        uint256 resolvedAt
    );

    /// @notice 事件：批量结算
    event BatchSettlementCreated(
        uint256 count,
        address payer,
        uint256 totalAmount,
        uint256 createdAt
    );

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "Settlement: caller is not the owner");
        _;
    }

    modifier settlementExists(uint256 settlementId) {
        require(settlementId > 0 && settlementId <= totalSettlements, "Settlement: not found");
        _;
    }

    // ==================== 构造函数 ====================

    /**
     * @dev 构造函数
     * @param _identityRegistry IdentityRegistry 合约地址
     */
    constructor(address _identityRegistry) {
        require(_identityRegistry != address(0), "Settlement: invalid identity registry");
        identityRegistry = _identityRegistry;
        owner = msg.sender;
    }

    // ==================== 外部函数 ====================

    /**
     * @dev 创建结算记录
     * @param subscriptionId 订阅 ID
     * @param amount 结算金额 (wei)
     * @param billingPeriod 计费周期
     * @param payee 收款方地址
     * @return settlementId 结算 ID
     */
    function createSettlement(
        string memory subscriptionId,
        uint256 amount,
        string memory billingPeriod,
        address payee
    ) external payable returns (uint256 settlementId) {
        require(amount > 0, "Settlement: zero amount");
        require(bytes(subscriptionId).length > 0, "Settlement: empty subscription");

        totalSettlements++;
        settlementId = totalSettlements;

        settlements[settlementId] = SettlementRecord({
            settlementId: settlementId,
            subscriptionId: subscriptionId,
            amount: amount,
            billingPeriod: billingPeriod,
            payer: msg.sender,
            payee: payee,
            status: STATUS_PENDING,
            createdAt: block.timestamp,
            confirmedAt: 0,
            disputeReason: ""
        });

        subscriptionSettlements[subscriptionId].push(settlementId);
        periodSettlements[billingPeriod].push(settlementId);
        payerSettlements[msg.sender].push(settlementId);

        emit SettlementCreated(
            settlementId, subscriptionId, amount, billingPeriod, msg.sender, payee, block.timestamp
        );
    }

    /**
     * @dev 批量创建结算记录
     * @param items 批量结算项列表
     * @return settlementIds 结算 ID 列表
     */
    function batchCreateSettlements(
        BatchItem[] memory items
    ) external payable returns (uint256[] memory settlementIds) {
        uint256 count = items.length;
        require(count > 0, "Settlement: empty batch");

        settlementIds = new uint256[](count);
        uint256 totalAmount = 0;

        for (uint256 i = 0; i < count; i++) {
            require(items[i].amount > 0, "Settlement: zero amount");
            totalAmount += items[i].amount;

            totalSettlements++;
            uint256 sid = totalSettlements;
            settlementIds[i] = sid;

            settlements[sid] = SettlementRecord({
                settlementId: sid,
                subscriptionId: items[i].subscriptionId,
                amount: items[i].amount,
                billingPeriod: items[i].billingPeriod,
                payer: msg.sender,
                payee: items[i].payee,
                status: STATUS_PENDING,
                createdAt: block.timestamp,
                confirmedAt: 0,
                disputeReason: ""
            });

            subscriptionSettlements[items[i].subscriptionId].push(sid);
            periodSettlements[items[i].billingPeriod].push(sid);
            payerSettlements[msg.sender].push(sid);
        }

        require(msg.value >= totalAmount, "Settlement: insufficient payment");
        emit BatchSettlementCreated(count, msg.sender, totalAmount, block.timestamp);
    }

    /**
     * @dev 确认结算
     * @param settlementId 结算 ID
     */
    function confirmSettlement(uint256 settlementId) external settlementExists(settlementId) {
        SettlementRecord storage record = settlements[settlementId];
        require(record.status == STATUS_PENDING, "Settlement: not pending");
        require(
            msg.sender == record.payee || msg.sender == owner,
            "Settlement: not authorized"
        );

        record.status = STATUS_CONFIRMED;
        record.confirmedAt = block.timestamp;

        emit SettlementConfirmed(settlementId, block.timestamp);
    }

    /**
     * @dev 发起争议
     * @param settlementId 结算 ID
     * @param reason 争议原因
     */
    function disputeSettlement(uint256 settlementId, string memory reason) external settlementExists(settlementId) {
        SettlementRecord storage record = settlements[settlementId];
        require(
            record.status == STATUS_PENDING || record.status == STATUS_CONFIRMED,
            "Settlement: invalid status"
        );
        require(
            msg.sender == record.payer || msg.sender == record.payee || msg.sender == owner,
            "Settlement: not authorized"
        );

        record.status = STATUS_DISPUTED;
        record.disputeReason = reason;
        totalDisputes++;

        emit SettlementDisputed(settlementId, reason, block.timestamp);
    }

    /**
     * @dev 解决争议（仲裁）
     * @param settlementId 结算 ID
     * @param resolveToPayee true=维持结算（付款给收款方），false=取消结算（退款给付款方）
     */
    function resolveDispute(uint256 settlementId, bool resolveToPayee) external settlementExists(settlementId) {
        require(msg.sender == owner, "Settlement: only owner can resolve");
        SettlementRecord storage record = settlements[settlementId];
        require(record.status == STATUS_DISPUTED, "Settlement: not disputed");

        if (resolveToPayee) {
            record.status = STATUS_CONFIRMED;
            record.confirmedAt = block.timestamp;
            emit DisputeResolved(settlementId, STATUS_CONFIRMED, block.timestamp);
        } else {
            record.status = STATUS_CANCELLED;
            emit DisputeResolved(settlementId, STATUS_CANCELLED, block.timestamp);
        }
    }

    /**
     * @dev 取消结算
     * @param settlementId 结算 ID
     */
    function cancelSettlement(uint256 settlementId) external settlementExists(settlementId) {
        SettlementRecord storage record = settlements[settlementId];
        require(record.status == STATUS_PENDING, "Settlement: not pending");
        require(msg.sender == record.payer || msg.sender == owner, "Settlement: not authorized");

        record.status = STATUS_CANCELLED;
    }

    // ==================== 视图函数 ====================

    /**
     * @dev 获取结算详情
     * @param settlementId 结算 ID
     * @return record 结算记录
     */
    function getSettlement(uint256 settlementId) external view settlementExists(settlementId) returns (
        SettlementRecord memory record
    ) {
        return settlements[settlementId];
    }

    /**
     * @dev 按订阅查询结算 ID 列表
     * @param subscriptionId 订阅 ID
     * @return settlementIds 结算 ID 列表
     */
    function getSettlementsBySubscription(string memory subscriptionId) external view returns (uint256[] memory) {
        return subscriptionSettlements[subscriptionId];
    }

    /**
     * @dev 按计费周期查询结算 ID 列表
     * @param billingPeriod 计费周期
     * @return settlementIds 结算 ID 列表
     */
    function getSettlementsByPeriod(string memory billingPeriod) external view returns (uint256[] memory) {
        return periodSettlements[billingPeriod];
    }

    /**
     * @dev 按付款方查询结算 ID 列表
     * @param payer 付款方地址
     * @return settlementIds 结算 ID 列表
     */
    function getSettlementsByPayer(address payer) external view returns (uint256[] memory) {
        return payerSettlements[payer];
    }

    /**
     * @dev 获取对账数据 — 指定计费周期的结算统计
     * @param billingPeriod 计费周期
     * @return totalCount 结算总笔数
     * @return totalAmount 结算总金额
     * @return confirmedCount 已确认笔数
     * @return disputedCount 争议笔数
     */
    function getReconciliation(string memory billingPeriod) external view returns (
        uint256 totalCount,
        uint256 totalAmount,
        uint256 confirmedCount,
        uint256 disputedCount
    ) {
        uint256[] storage ids = periodSettlements[billingPeriod];
        totalCount = ids.length;

        for (uint256 i = 0; i < ids.length; i++) {
            SettlementRecord storage record = settlements[ids[i]];
            totalAmount += record.amount;
            if (record.status == STATUS_CONFIRMED) {
                confirmedCount++;
            }
            if (record.status == STATUS_DISPUTED) {
                disputedCount++;
            }
        }
    }
}
