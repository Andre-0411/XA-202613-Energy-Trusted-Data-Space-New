// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title DataAuthorization
 * @notice 数据授权访问合约 —— 管理数据资产的授权、访问控制和有效期
 * @dev 基于 ACL（访问控制列表）模式，支持授权发放与撤销
 */
contract DataAuthorization {
    /// @notice 授权信息结构体
    struct Authorization {
        address grantor;       // 授权方
        address grantee;       // 被授权方
        uint256 assetId;       // 资产 ID
        uint256 grantedAt;     // 授权时间
        uint256 expiresAt;     // 过期时间（0 表示永不过期）
        bool revoked;          // 是否已撤销
    }

    /// @notice 授权 ID → 授权信息
    mapping(uint256 => Authorization) private authorizations;

    /// @notice 授权 ID 自增计数器
    uint256 public nextAuthId;

    /// @notice (grantor, grantee, assetId) → 授权 ID（用于快速查找）
    mapping(bytes32 => uint256) private authLookup;

    /// @notice 地址 → 授权的授权 ID 列表（作为授权方）
    mapping(address => uint256[]) private grantorAuths;

    /// @notice 地址 → 授权的授权 ID 列表（作为被授权方）
    mapping(address => uint256[]) private granteeAuths;

    /// @notice 合约拥有者
    address public owner;

    // ==================== 事件 ====================

    /// @notice 访问授权事件
    event AccessGranted(
        uint256 indexed authId,
        address indexed grantor,
        address indexed grantee,
        uint256 assetId,
        uint256 expiresAt
    );

    /// @notice 访问撤销事件
    event AccessRevoked(uint256 indexed authId, address indexed revoker, uint256 timestamp);

    // ==================== 修饰符 ====================

    modifier onlyOwner() {
        require(msg.sender == owner, "DataAuthorization: caller is not the owner");
        _;
    }

    modifier validAuth(uint256 _authId) {
        require(authorizations[_authId].grantor != address(0), "DataAuthorization: auth does not exist");
        _;
    }

    // ==================== 构造函数 ====================

    constructor() {
        owner = msg.sender;
        nextAuthId = 1;
    }

    // ==================== 外部函数 ====================

    /**
     * @notice 授权访问
     * @param _grantee 被授权方地址
     * @param _assetId 数据资产 ID
     * @param _duration 授权有效期（秒，0 表示永不过期）
     * @return authId 授权 ID
     */
    function grantAccess(address _grantee, uint256 _assetId, uint256 _duration) external returns (uint256 authId) {
        require(_grantee != address(0), "DataAuthorization: invalid grantee");
        require(_grantee != msg.sender, "DataAuthorization: cannot authorize self");

        // 检查是否已存在有效授权
        bytes32 lookupKey = keccak256(abi.encodePacked(msg.sender, _grantee, _assetId));
        uint256 existingId = authLookup[lookupKey];
        if (existingId > 0) {
            Authorization storage existing = authorizations[existingId];
            require(existing.revoked || (existing.expiresAt != 0 && block.timestamp >= existing.expiresAt),
                "DataAuthorization: active authorization already exists");
        }

        authId = nextAuthId++;
        uint256 expiresAt = _duration > 0 ? block.timestamp + _duration : 0;

        authorizations[authId] = Authorization({
            grantor: msg.sender,
            grantee: _grantee,
            assetId: _assetId,
            grantedAt: block.timestamp,
            expiresAt: expiresAt,
            revoked: false
        });

        authLookup[lookupKey] = authId;
        grantorAuths[msg.sender].push(authId);
        granteeAuths[_grantee].push(authId);

        emit AccessGranted(authId, msg.sender, _grantee, _assetId, expiresAt);
    }

    /**
     * @notice 撤销授权（授权方或合约拥有者可操作）
     * @param _authId 授权 ID
     */
    function revokeAccess(uint256 _authId) external validAuth(_authId) {
        Authorization storage auth = authorizations[_authId];
        require(msg.sender == auth.grantor || msg.sender == owner, "DataAuthorization: not authorized to revoke");
        require(!auth.revoked, "DataAuthorization: already revoked");

        auth.revoked = true;
        emit AccessRevoked(_authId, msg.sender, block.timestamp);
    }

    /**
     * @notice 检查某地址是否有权访问指定资产
     * @param _grantee 被授权方地址
     * @param _assetId 资产 ID
     * @return isAuthorized 是否有权限
     */
    function isAuthorized(address _grantee, uint256 _assetId) external view returns (bool isAuthorized) {
        bytes32 lookupKey = keccak256(abi.encodePacked(msg.sender, _grantee, _assetId));
        uint256 authId = authLookup[lookupKey];
        if (authId == 0) return false;

        Authorization storage auth = authorizations[authId];
        if (auth.revoked) return false;
        if (auth.expiresAt != 0 && block.timestamp >= auth.expiresAt) return false;

        return true;
    }

    /**
     * @notice 查询授权详情
     * @param _authId 授权 ID
     * @return grantor 授权方
     * @return grantee 被授权方
     * @return assetId 资产 ID
     * @return grantedAt 授权时间
     * @return expiresAt 过期时间
     * @return revoked 是否已撤销
     */
    function getAuthorization(uint256 _authId)
        external
        view
        validAuth(_authId)
        returns (
            address grantor,
            address grantee,
            uint256 assetId,
            uint256 grantedAt,
            uint256 expiresAt,
            bool revoked
        )
    {
        Authorization storage auth = authorizations[_authId];
        return (auth.grantor, auth.grantee, auth.assetId, auth.grantedAt, auth.expiresAt, auth.revoked);
    }

    /**
     * @notice 查询用户作为授权方的授权数量
     * @param _user 用户地址
     * @return count 授权数量
     */
    function getGrantorAuthCount(address _user) external view returns (uint256 count) {
        return grantorAuths[_user].length;
    }

    /**
     * @notice 查询用户作为被授权方的授权数量
     * @param _user 用户地址
     * @return count 授权数量
     */
    function getGranteeAuthCount(address _user) external view returns (uint256 count) {
        return granteeAuths[_user].length;
    }
}
