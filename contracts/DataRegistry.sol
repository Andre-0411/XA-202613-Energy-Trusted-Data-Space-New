// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

/**
 * @title DataRegistry
 * @dev 数据注册中心合约
 *
 * 管理数据资产的链上注册、更新、查询。
 * 与 IdentityRegistry 集成进行身份验证。
 *
 * 功能:
 * - 数据资产注册
 * - 数据资产元数据更新
 * - 数据资产分类管理
 * - 注册数据查询
 */
contract DataRegistry {
    // ==================== 状态变量 ====================

    /// @notice IdentityRegistry 合约地址
    address public identityRegistry;

    /// @notice 合约所有者
    address public owner;

    /// @notice 数据资产注册总数
    uint256 public totalRegistered;

    // ==================== 数据结构 ====================

    /// @notice 数据资产信息
    struct DataAsset {
        string assetId;           // 资产 ID
        string ownerDid;          // 所有者 DID
        string name;              // 资产名称
        string category;          // 资产分类
        uint8 classificationLevel; // 分类级别 (1-4)
        string dataHash;          // 数据 SM3 哈希
        string metadataUri;       // 元数据 URI
        uint256 registeredAt;     // 注册时间
        uint256 updatedAt;        // 更新时间
        bool isActive;            // 是否有效
    }

    /// @notice 事件：数据资产注册
    event DataRegistered(
        string indexed assetId,
        string indexed ownerDid,
        string name,
        string category,
        uint8 classificationLevel,
        uint256 registeredAt
    );

    /// @notice 事件：数据资产更新
    event DataUpdated(
        string indexed assetId,
        string name,
        string metadataUri,
        uint256 updatedAt
    );

    /// @notice 事件：数据资产注销
    event DataDeactivated(
        string indexed assetId,
        uint256 deactivatedAt
    );

    // ==================== 映射 ====================

    /// @notice assetId => DataAsset
    mapping(string => DataAsset) private assets;

    /// @notice ownerDid => assetId[]
    mapping(string => string[]) private ownerAssets;

    /// @notice category => assetId[]
    mapping(string => string[]) private categoryAssets;

    /// @notice assetId 是否已注册
    mapping(string => bool) private isRegistered;

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "DataRegistry: caller is not the owner");
        _;
    }

    modifier assetExists(string memory assetId) {
        require(isRegistered[assetId], "DataRegistry: asset not registered");
        _;
    }

    // ==================== 构造函数 ====================

    /**
     * @dev 构造函数
     * @param _identityRegistry IdentityRegistry 合约地址
     */
    constructor(address _identityRegistry) {
        require(_identityRegistry != address(0), "DataRegistry: invalid identity registry");
        identityRegistry = _identityRegistry;
        owner = msg.sender;
    }

    // ==================== 外部函数 ====================

    /**
     * @dev 注册数据资产
     * @param assetId 资产 ID
     * @param ownerDid 所有者 DID
     * @param name 资产名称
     * @param category 资产分类
     * @param classificationLevel 分类级别 (1-4)
     * @param dataHash 数据 SM3 哈希
     * @param metadataUri 元数据 URI
     */
    function registerData(
        string memory assetId,
        string memory ownerDid,
        string memory name,
        string memory category,
        uint8 classificationLevel,
        string memory dataHash,
        string memory metadataUri
    ) external {
        require(bytes(assetId).length > 0, "DataRegistry: empty assetId");
        require(!isRegistered[assetId], "DataRegistry: already registered");
        require(classificationLevel >= 1 && classificationLevel <= 4, "DataRegistry: invalid level");

        uint256 now_ts = block.timestamp;

        assets[assetId] = DataAsset({
            assetId: assetId,
            ownerDid: ownerDid,
            name: name,
            category: category,
            classificationLevel: classificationLevel,
            dataHash: dataHash,
            metadataUri: metadataUri,
            registeredAt: now_ts,
            updatedAt: now_ts,
            isActive: true
        });

        isRegistered[assetId] = true;
        ownerAssets[ownerDid].push(assetId);
        categoryAssets[category].push(assetId);
        totalRegistered++;

        emit DataRegistered(assetId, ownerDid, name, category, classificationLevel, now_ts);
    }

    /**
     * @dev 更新数据资产元数据
     * @param assetId 资产 ID
     * @param name 新名称
     * @param metadataUri 新元数据 URI
     * @param dataHash 新数据哈希
     */
    function updateData(
        string memory assetId,
        string memory name,
        string memory metadataUri,
        string memory dataHash
    ) external assetExists(assetId) {
        DataAsset storage asset = assets[assetId];
        require(
            keccak256(bytes(asset.ownerDid)) == keccak256(bytes(msg.sender == owner ? asset.ownerDid : "")) ||
            msg.sender == owner,
            "DataRegistry: not authorized"
        );

        if (bytes(name).length > 0) {
            asset.name = name;
        }
        if (bytes(metadataUri).length > 0) {
            asset.metadataUri = metadataUri;
        }
        if (bytes(dataHash).length > 0) {
            asset.dataHash = dataHash;
        }
        asset.updatedAt = block.timestamp;

        emit DataUpdated(assetId, asset.name, asset.metadataUri, block.timestamp);
    }

    /**
     * @dev 注销数据资产
     * @param assetId 资产 ID
     */
    function deactivateData(string memory assetId) external assetExists(assetId) {
        DataAsset storage asset = assets[assetId];
        require(
            msg.sender == owner,
            "DataRegistry: not authorized"
        );

        asset.isActive = false;
        asset.updatedAt = block.timestamp;

        emit DataDeactivated(assetId, block.timestamp);
    }

    // ==================== 视图函数 ====================

    /**
     * @dev 获取数据资产信息
     * @param assetId 资产 ID
     * @return 数据资产信息
     */
    function getData(string memory assetId) external view assetExists(assetId) returns (
        string memory _assetId,
        string memory _ownerDid,
        string memory _name,
        string memory _category,
        uint8 _classificationLevel,
        string memory _dataHash,
        string memory _metadataUri,
        uint256 _registeredAt,
        uint256 _updatedAt,
        bool _isActive
    ) {
        DataAsset storage asset = assets[assetId];
        return (
            asset.assetId,
            asset.ownerDid,
            asset.name,
            asset.category,
            asset.classificationLevel,
            asset.dataHash,
            asset.metadataUri,
            asset.registeredAt,
            asset.updatedAt,
            asset.isActive
        );
    }

    /**
     * @dev 检查资产是否已注册
     * @param assetId 资产 ID
     * @return 是否已注册
     */
    function isDataRegistered(string memory assetId) external view returns (bool) {
        return isRegistered[assetId];
    }

    /**
     * @dev 获取指定所有者的资产列表
     * @param ownerDid 所有者 DID
     * @return 资产 ID 列表
     */
    function getAssetsByOwner(string memory ownerDid) external view returns (string[] memory) {
        return ownerAssets[ownerDid];
    }

    /**
     * @dev 获取指定分类的资产列表
     * @param category 资产分类
     * @return 资产 ID 列表
     */
    function getAssetsByCategory(string memory category) external view returns (string[] memory) {
        return categoryAssets[category];
    }
}
