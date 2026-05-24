// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title DataAssetRights
 * @notice 数据资产确权合约 —— 负责数据资产的注册、转让和查询
 * @dev 使用 mapping 管理资产所有权，支持事件驱动的链上存证
 */
contract DataAssetRights {
    /// @notice 资产信息结构体
    struct Asset {
        uint256 assetId;
        address owner;
        bytes32 hash;
        string metadata;
        uint256 registeredAt;
        bool exists;
    }

    /// @notice 资产 ID → 资产信息
    mapping(uint256 => Asset) private assets;

    /// @notice 地址 → 拥有的资产 ID 列表
    mapping(address => uint256[]) private ownerAssets;

    /// @notice 资产 ID 自增计数器
    uint256 public nextAssetId;

    /// @notice 合约拥有者
    address public owner;

    // ==================== 事件 ====================

    /// @notice 资产注册事件
    event AssetRegistered(uint256 indexed assetId, address indexed owner, bytes32 hash, string metadata, uint256 timestamp);

    /// @notice 资产转让事件
    event AssetTransferred(uint256 indexed assetId, address indexed from, address indexed to, uint256 timestamp);

    // ==================== 修饰符 ====================

    /// @notice 仅合约拥有者可调用
    modifier onlyOwner() {
        require(msg.sender == owner, "DataAssetRights: caller is not the owner");
        _;
    }

    /// @notice 资产必须存在
    modifier validAsset(uint256 _assetId) {
        require(assets[_assetId].exists, "DataAssetRights: asset does not exist");
        _;
    }

    /// @notice 仅资产拥有者可调用
    modifier onlyAssetOwner(uint256 _assetId) {
        require(msg.sender == assets[_assetId].owner, "DataAssetRights: caller is not the asset owner");
        _;
    }

    // ==================== 构造函数 ====================

    constructor() {
        owner = msg.sender;
        nextAssetId = 1;
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 注册新的数据资产
     * @param _hash 数据哈希（链上指纹）
     * @param _metadata 元数据描述（JSON 字符串）
     * @return assetId 新注册的资产 ID
     */
    function registerAsset(bytes32 _hash, string calldata _metadata) external returns (uint256 assetId) {
        require(_hash != bytes32(0), "DataAssetRights: hash cannot be empty");

        assetId = nextAssetId++;
        assets[assetId] = Asset({
            assetId: assetId,
            owner: msg.sender,
            hash: _hash,
            metadata: _metadata,
            registeredAt: block.timestamp,
            exists: true
        });
        ownerAssets[msg.sender].push(assetId);

        emit AssetRegistered(assetId, msg.sender, _hash, _metadata, block.timestamp);
    }

    /**
     * @notice 转让数据资产给新拥有者
     * @param _assetId 资产 ID
     * @param _to 新拥有者地址
     */
    function transferAsset(uint256 _assetId, address _to) external validAsset(_assetId) onlyAssetOwner(_assetId) {
        require(_to != address(0), "DataAssetRights: cannot transfer to zero address");
        require(_to != msg.sender, "DataAssetRights: cannot transfer to self");

        assets[_assetId].owner = _to;
        ownerAssets[_to].push(_assetId);

        emit AssetTransferred(_assetId, msg.sender, _to, block.timestamp);
    }

    /**
     * @notice 查询资产详情
     * @param _assetId 资产 ID
     * @return assetOwner 资产拥有者地址
     * @return hash 数据哈希
     * @return metadata 元数据
     * @return registeredAt 注册时间
     */
    function getAsset(uint256 _assetId)
        external
        view
        validAsset(_assetId)
        returns (
            address assetOwner,
            bytes32 hash,
            string memory metadata,
            uint256 registeredAt
        )
    {
        Asset storage a = assets[_assetId];
        return (a.owner, a.hash, a.metadata, a.registeredAt);
    }

    /**
     * @notice 查询某地址拥有的资产数量
     * @param _owner 拥有者地址
     * @return count 资产数量
     */
    function getOwnerAssetCount(address _owner) external view returns (uint256 count) {
        return ownerAssets[_owner].length;
    }

    /**
     * @notice 查询某地址拥有的资产 ID 列表
     * @param _owner 拥有者地址
     * @return assetIds 资产 ID 数组
     */
    function getOwnerAssets(address _owner) external view returns (uint256[] memory assetIds) {
        return ownerAssets[_owner];
    }
}
