// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IncentiveDistribution
 * @notice 激励分红合约 —— 管理激励池、贡献度计算和分红发放
 * @dev 支持多激励池管理，按贡献度比例分配激励
 */
contract IncentiveDistribution {
    /// @notice 激励池结构体
    struct IncentivePool {
        uint256 poolId;
        string name;
        uint256 totalAmount;       // 池子总金额（wei）
        uint256 distributedAmount; // 已分配金额
        uint256 createdAt;
        bool active;
    }

    /// @notice 贡献记录结构体
    struct Contribution {
        address contributor;
        uint256 poolId;
        uint256 score;             // 贡献度分数
        uint256 rewardAmount;      // 应得奖励金额
        uint256 claimedAmount;     // 已领取金额
        bool exists;
    }

    /// @notice 池子 ID → 池子信息
    mapping(uint256 => IncentivePool) private pools;

    /// @notice (池子 ID, 贡献者地址) → 贡献记录
    mapping(uint256 => mapping(address => Contribution)) private contributions;

    /// @notice 池子 ID → 贡献者地址列表
    mapping(uint256 => address[]) private poolContributors;

    /// @notice 池子 ID 自增计数器
    uint256 public nextPoolId;

    /// @notice 合约拥有者
    address public owner;

    // ==================== 事件 ====================

    /// @notice 激励池创建事件
    event IncentivePoolCreated(uint256 indexed poolId, string name, uint256 totalAmount, uint256 timestamp);

    /// @notice 奖励分配事件
    event RewardDistributed(uint256 indexed poolId, address indexed contributor, uint256 amount, uint256 timestamp);

    /// @notice 贡献记录事件
    event ContributionRecorded(uint256 indexed poolId, address indexed contributor, uint256 score, uint256 timestamp);

    /// @notice 激励池资金注入事件
    event PoolFunded(uint256 indexed poolId, uint256 amount, uint256 timestamp);

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "IncentiveDistribution: caller is not the owner");
        _;
    }

    modifier validPool(uint256 _poolId) {
        require(pools[_poolId].poolId != 0, "IncentiveDistribution: pool does not exist");
        _;
    }

    modifier poolActive(uint256 _poolId) {
        require(pools[_poolId].active, "IncentiveDistribution: pool is not active");
        _;
    }

    // ==================== 构造函数 ====================

    constructor() {
        owner = msg.sender;
        nextPoolId = 1;
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 创建激励池
     * @param _name 池子名称
     * @return poolId 新池子 ID
     */
    function createPool(string calldata _name) external payable onlyOwner returns (uint256 poolId) {
        require(msg.value > 0, "IncentiveDistribution: initial funding required");
        require(_name.length > 0, "IncentiveDistribution: name cannot be empty");

        poolId = nextPoolId++;
        pools[poolId] = IncentivePool({
            poolId: poolId,
            name: _name,
            totalAmount: msg.value,
            distributedAmount: 0,
            createdAt: block.timestamp,
            active: true
        });

        emit IncentivePoolCreated(poolId, _name, msg.value, block.timestamp);
    }

    /**
     * @notice 向激励池注入资金
     * @param _poolId 池子 ID
     */
    function fundPool(uint256 _poolId) external payable validPool(_poolId) poolActive(_poolId) {
        require(msg.value > 0, "IncentiveDistribution: funding amount must be positive");

        pools[_poolId].totalAmount += msg.value;
        emit PoolFunded(_poolId, msg.value, block.timestamp);
    }

    /**
     * @notice 记录贡献度（仅合约拥有者可操作）
     * @param _poolId 池子 ID
     * @param _contributor 贡献者地址
     * @param _score 贡献度分数
     */
    function recordContribution(uint256 _poolId, address _contributor, uint256 _score)
        external
        onlyOwner
        validPool(_poolId)
        poolActive(_poolId)
    {
        require(_contributor != address(0), "IncentiveDistribution: invalid contributor");
        require(_score > 0, "IncentiveDistribution: score must be positive");

        Contribution storage c = contributions[_poolId][_contributor];
        if (!c.exists) {
            poolContributors[_poolId].push(_contributor);
            c.contributor = _contributor;
            c.poolId = _poolId;
            c.exists = true;
        }
        c.score += _score;

        emit ContributionRecorded(_poolId, _contributor, _score, block.timestamp);
    }

    /**
     * @notice 计算并分配奖励（仅合约拥有者可操作）
     * @dev 根据贡献度分数占总分的比例分配池中剩余资金
     * @param _poolId 池子 ID
     */
    function distributeRewards(uint256 _poolId) external onlyOwner validPool(_poolId) {
        IncentivePool storage pool = pools[_poolId];
        require(pool.distributedAmount < pool.totalAmount, "IncentiveDistribution: all rewards distributed");

        address[] storage contributors = poolContributors[_poolId];
        require(contributors.length > 0, "IncentiveDistribution: no contributors");

        // 计算总分
        uint256 totalScore = 0;
        for (uint256 i = 0; i < contributors.length; i++) {
            totalScore += contributions[_poolId][contributors[i]].score;
        }
        require(totalScore > 0, "IncentiveDistribution: total score is zero");

        uint256 distributable = pool.totalAmount - pool.distributedAmount;

        // 按比例分配
        for (uint256 i = 0; i < contributors.length; i++) {
            Contribution storage c = contributions[_poolId][contributors[i]];
            uint256 reward = (distributable * c.score) / totalScore;
            if (reward > 0) {
                c.rewardAmount += reward;
                pool.distributedAmount += reward;

                // 转账
                (bool success, ) = payable(c.contributor).call{value: reward}("");
                require(success, "IncentiveDistribution: transfer failed");

                c.claimedAmount += reward;
                emit RewardDistributed(_poolId, c.contributor, reward, block.timestamp);
            }
        }
    }

    /**
     * @notice 查询激励池详情
     * @param _poolId 池子 ID
     * @return name 池子名称
     * @return totalAmount 总金额
     * @return distributedAmount 已分配金额
     * @return createdAt 创建时间
     * @return active 是否活跃
     */
    function getPool(uint256 _poolId)
        external
        view
        validPool(_poolId)
        returns (
            string memory name,
            uint256 totalAmount,
            uint256 distributedAmount,
            uint256 createdAt,
            bool active
        )
    {
        IncentivePool storage p = pools[_poolId];
        return (p.name, p.totalAmount, p.distributedAmount, p.createdAt, p.active);
    }

    /**
     * @notice 查询贡献者的奖励信息
     * @param _poolId 池子 ID
     * @param _contributor 贡献者地址
     * @return score 贡献度分数
     * @return rewardAmount 应得奖励
     * @return claimedAmount 已领取金额
     */
    function getContribution(uint256 _poolId, address _contributor)
        external
        view
        returns (uint256 score, uint256 rewardAmount, uint256 claimedAmount)
    {
        Contribution storage c = contributions[_poolId][_contributor];
        return (c.score, c.rewardAmount, c.claimedAmount);
    }

    /**
     * @notice 关闭激励池
     * @param _poolId 池子 ID
     */
    function deactivatePool(uint256 _poolId) external onlyOwner validPool(_poolId) {
        pools[_poolId].active = false;
    }

    /**
     * @notice 查询池子中的贡献者数量
     * @param _poolId 池子 ID
     * @return count 贡献者数量
     */
    function getContributorCount(uint256 _poolId) external view validPool(_poolId) returns (uint256 count) {
        return poolContributors[_poolId].length;
    }

    /**
     * @notice 接收以太坊（用于向合约充值）
     */
    receive() external payable {}
}
