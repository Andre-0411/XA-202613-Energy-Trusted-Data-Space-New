// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title DataTrading
 * @notice 数据交易合约 —— 管理数据资产的买卖交易流程
 * @dev 支持创建订单、确认/取消、交易完成与资金结算
 */
contract DataTrading {
    /// @notice 订单状态枚举
    enum OrderStatus { Created, Confirmed, Completed, Cancelled }

    /// @notice 交易订单结构体
    struct Order {
        uint256 orderId;
        address buyer;
        address seller;
        uint256 assetId;
        uint256 price;
        OrderStatus status;
        uint256 createdAt;
        uint256 completedAt;
    }

    /// @notice 订单 ID → 订单信息
    mapping(uint256 => Order) private orders;

    /// @notice 地址 → 参与的订单 ID 列表
    mapping(address => uint256[]) private userOrders;

    /// @notice 订单 ID 自增计数器
    uint256 public nextOrderId;

    /// @notice 合约拥有者
    address public owner;

    /// @notice 平台手续费比例（万分之几，如 200 = 2%）
    uint256 public feeRate;

    /// @notice 手续费接收地址
    address public feeRecipient;

    // ==================== 事件 ====================

    /// @notice 订单创建事件
    event OrderCreated(uint256 indexed orderId, address indexed buyer, address indexed seller, uint256 assetId, uint256 price);

    /// @notice 订单确认事件
    event OrderConfirmed(uint256 indexed orderId, address indexed confirmer);

    /// @notice 订单完成事件
    event OrderCompleted(uint256 indexed orderId, uint256 settledAmount);

    /// @notice 订单取消事件
    event OrderCancelled(uint256 indexed orderId, address indexed canceller);

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "DataTrading: caller is not the owner");
        _;
    }

    modifier validOrder(uint256 _orderId) {
        require(orders[_orderId].orderId != 0, "DataTrading: order does not exist");
        _;
    }

    // ==================== 构造函数 ====================

    constructor(uint256 _feeRate, address _feeRecipient) {
        require(_feeRate <= 10000, "DataTrading: fee rate too high");
        require(_feeRecipient != address(0), "DataTrading: invalid fee recipient");
        owner = msg.sender;
        feeRate = _feeRate;
        feeRecipient = _feeRecipient;
        nextOrderId = 1;
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 创建交易订单（买家发起）
     * @param _seller 卖家地址
     * @param _assetId 数据资产 ID
     * @param _price 交易价格（wei）
     * @return orderId 新订单 ID
     */
    function createOrder(address _seller, uint256 _assetId, uint256 _price) external payable returns (uint256 orderId) {
        require(_seller != address(0), "DataTrading: invalid seller");
        require(_seller != msg.sender, "DataTrading: cannot trade with self");
        require(_price > 0, "DataTrading: price must be positive");
        require(msg.value >= _price, "DataTrading: insufficient payment");

        orderId = nextOrderId++;
        orders[orderId] = Order({
            orderId: orderId,
            buyer: msg.sender,
            seller: _seller,
            assetId: _assetId,
            price: _price,
            status: OrderStatus.Created,
            createdAt: block.timestamp,
            completedAt: 0
        });

        userOrders[msg.sender].push(orderId);
        userOrders[_seller].push(orderId);

        emit OrderCreated(orderId, msg.sender, _seller, _assetId, _price);
    }

    /**
     * @notice 确认订单（卖家确认）
     * @param _orderId 订单 ID
     */
    function confirmOrder(uint256 _orderId) external validOrder(_orderId) {
        Order storage o = orders[_orderId];
        require(msg.sender == o.seller, "DataTrading: only seller can confirm");
        require(o.status == OrderStatus.Created, "DataTrading: order not in Created status");

        o.status = OrderStatus.Confirmed;
        emit OrderConfirmed(_orderId, msg.sender);
    }

    /**
     * @notice 完成交易（触发结算，将资金转给卖家）
     * @param _orderId 订单 ID
     */
    function completeOrder(uint256 _orderId) external validOrder(_orderId) {
        Order storage o = orders[_orderId];
        require(msg.sender == o.buyer, "DataTrading: only buyer can complete");
        require(o.status == OrderStatus.Confirmed, "DataTrading: order not confirmed");

        o.status = OrderStatus.Completed;
        o.completedAt = block.timestamp;

        // 计算手续费
        uint256 fee = (o.price * feeRate) / 10000;
        uint256 sellerAmount = o.price - fee;

        // 转账给卖家
        (bool successSeller, ) = payable(o.seller).call{value: sellerAmount}("");
        require(successSeller, "DataTrading: seller transfer failed");

        // 转账手续费
        if (fee > 0) {
            (bool successFee, ) = payable(feeRecipient).call{value: fee}("");
            require(successFee, "DataTrading: fee transfer failed");
        }

        emit OrderCompleted(_orderId, sellerAmount);
    }

    /**
     * @notice 取消订单（买家或卖家可取消，仅限 Created 状态）
     * @param _orderId 订单 ID
     */
    function cancelOrder(uint256 _orderId) external validOrder(_orderId) {
        Order storage o = orders[_orderId];
        require(msg.sender == o.buyer || msg.sender == o.seller, "DataTrading: not a participant");
        require(o.status == OrderStatus.Created, "DataTrading: cannot cancel in current status");

        o.status = OrderStatus.Cancelled;

        // 退款给买家
        (bool success, ) = payable(o.buyer).call{value: o.price}("");
        require(success, "DataTrading: refund failed");

        emit OrderCancelled(_orderId, msg.sender);
    }

    /**
     * @notice 查询订单详情
     * @param _orderId 订单 ID
     * @return orderData 订单数据
     */
    function getOrder(uint256 _orderId)
        external
        view
        validOrder(_orderId)
        returns (
            uint256 orderId,
            address buyer,
            address seller,
            uint256 assetId,
            uint256 price,
            OrderStatus status,
            uint256 createdAt,
            uint256 completedAt
        )
    {
        Order storage o = orders[_orderId];
        return (o.orderId, o.buyer, o.seller, o.assetId, o.price, o.status, o.createdAt, o.completedAt);
    }

    /**
     * @notice 查询用户参与的订单数量
     * @param _user 用户地址
     * @return count 订单数量
     */
    function getUserOrderCount(address _user) external view returns (uint256 count) {
        return userOrders[_user].length;
    }
}
