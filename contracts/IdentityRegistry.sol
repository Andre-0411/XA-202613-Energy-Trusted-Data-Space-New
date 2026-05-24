// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IIdentityRegistry.sol";

/**
 * @title IdentityRegistry
 * @notice DID 身份注册合约 - 管理能源数据空间中的去中心化身份
 * @dev 实现 IIdentityRegistry 接口，支持角色化身份管理、公钥更新、管理员转移
 */
contract IdentityRegistry is IIdentityRegistry {
    /// @notice 管理员地址
    address public admin;

    /// @notice DID => 身份信息
    mapping(string => Identity) private identities;

    /// @notice DID => 注册地址
    mapping(string => address) private didToAddress;

    /// @notice 地址 => DID 列表
    mapping(address => string[]) private addressToDids;

    /// @notice 构造函数，设置初始管理员
    constructor() {
        admin = msg.sender;
    }

    /**
     * @notice 注册新身份
     * @param did 去中心化身份标识
     * @param publicKey 公钥（PEM/hex 编码）
     * @param role 角色：0=普通用户, 1=数据提供方, 2=数据使用方, 3=监管方, 4=平台管理员
     */
    function registerIdentity(
        string calldata did,
        string calldata publicKey,
        uint8 role
    ) external override {
        require(bytes(did).length > 0, "DID cannot be empty");
        require(bytes(publicKey).length > 0, "Public key cannot be empty");
        require(role <= 4, "Invalid role");
        require(!identities[did].isActive, "DID already registered");

        identities[did] = Identity({
            did: did,
            publicKey: publicKey,
            role: role,
            isActive: true,
            registeredAt: block.timestamp,
            updatedAt: block.timestamp
        });

        didToAddress[did] = msg.sender;
        addressToDids[msg.sender].push(did);

        emit IdentityRegistered(did, msg.sender, role);
    }

    /**
     * @notice 注销身份
     * @param did 要注销的 DID
     */
    function revokeIdentity(string calldata did) external override {
        require(identities[did].isActive, "DID not active");
        require(
            didToAddress[did] == msg.sender || msg.sender == admin,
            "Not authorized"
        );

        identities[did].isActive = false;
        identities[did].updatedAt = block.timestamp;

        emit IdentityRevoked(did);
    }

    /**
     * @notice 验证身份是否有效
     * @param did 要验证的 DID
     * @return 是否有效
     */
    function verifyIdentity(string calldata did) external view override returns (bool) {
        return identities[did].isActive;
    }

    /**
     * @notice 获取身份信息
     * @param did 要查询的 DID
     * @return identity 身份信息结构体
     */
    function getIdentity(string calldata did) external view override returns (Identity memory) {
        require(identities[did].isActive, "DID not found or inactive");
        return identities[did];
    }

    /**
     * @notice 更新公钥
     * @param did DID 标识
     * @param newPublicKey 新公钥
     */
    function updatePublicKey(string calldata did, string calldata newPublicKey) external override {
        require(identities[did].isActive, "DID not active");
        require(
            didToAddress[did] == msg.sender || msg.sender == admin,
            "Not authorized"
        );
        require(bytes(newPublicKey).length > 0, "Public key cannot be empty");

        identities[did].publicKey = newPublicKey;
        identities[did].updatedAt = block.timestamp;
    }

    /**
     * @notice 检查 DID 是否已注册且有效
     * @param did DID 标识
     * @return 是否已注册
     */
    function isRegistered(string calldata did) external view override returns (bool) {
        return identities[did].isActive;
    }

    /**
     * @notice 转移管理员权限
     * @param newAdmin 新管理员地址
     */
    function transferAdmin(address newAdmin) external override {
        require(msg.sender == admin, "Only admin");
        require(newAdmin != address(0), "Invalid address");

        admin = newAdmin;
    }

    /**
     * @notice 获取某地址关联的所有 DID
     * @param owner 地址
     * @return DID 列表
     */
    function getDidsByAddress(address owner) external view returns (string[] memory) {
        return addressToDids[owner];
    }
}
