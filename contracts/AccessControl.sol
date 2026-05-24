// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IAccessControl.sol";
import "./interfaces/IIdentityRegistry.sol";
import "./interfaces/IDataAssetNFT.sol";

/**
 * @title AccessControl
 * @notice 访问控制合约 - 管理数据资产的细粒度访问权限
 * @dev 实现 IAccessControl 接口，支持策略化访问管理，关联身份和 NFT 合约
 */
contract AccessControl is IAccessControl {
    /// @notice 身份注册中心
    IIdentityRegistry public identityRegistry;

    /// @notice 数据资产 NFT 合约
    IDataAssetNFT public dataAssetNFT;

    /// @notice 合约管理员
    address public admin;

    /// @notice 策略 ID 计数器
    uint256 private _policyIdCounter;

    /// @notice policyId => 策略
    mapping(uint256 => AccessPolicy) private _policies;

    /// @notice tokenId => grantee => policyId（授权映射）
    mapping(uint256 => mapping(address => uint256)) private _tokenGranteePolicy;

    /// @notice tokenId => 已授权地址列表
    mapping(uint256 => address[]) private _tokenGrantees;

    /// @notice 构造函数
    /// @param _identityRegistry 身份注册中心地址
    /// @param _dataAssetNFT 数据资产 NFT 地址
    constructor(address _identityRegistry, address _dataAssetNFT) {
        identityRegistry = IIdentityRegistry(_identityRegistry);
        dataAssetNFT = IDataAssetNFT(_dataAssetNFT);
        admin = msg.sender;
    }

    /**
     * @notice 创建访问策略
     * @param tokenId 资产 tokenId
     * @param accessLevel 访问级别：1=只读, 2=计算, 3=导出, 4=管理
     * @param expiresAt 过期时间（Unix 时间戳，0 表示永不过期）
     * @param conditions JSON 格式附加条件
     * @return policyId 创建的策略 ID
     */
    function createPolicy(
        uint256 tokenId,
        uint8 accessLevel,
        uint256 expiresAt,
        string calldata conditions
    ) external override returns (uint256) {
        require(accessLevel >= 1 && accessLevel <= 4, "Invalid access level");
        require(expiresAt == 0 || expiresAt > block.timestamp, "Invalid expiry");

        _policyIdCounter++;

        _policies[_policyIdCounter] = AccessPolicy({
            tokenId: tokenId,
            accessLevel: accessLevel,
            expiresAt: expiresAt,
            conditions: conditions,
            isActive: true
        });

        emit PolicyCreated(_policyIdCounter, tokenId);
        return _policyIdCounter;
    }

    /**
     * @notice 授权某地址访问指定 tokenId（使用指定策略）
     * @param tokenId 资产 tokenId
     * @param grantee 被授权地址
     * @param policyId 策略 ID
     */
    function grantAccess(uint256 tokenId, address grantee, uint256 policyId) external override {
        require(grantee != address(0), "Invalid grantee");
        require(_policies[policyId].isActive, "Policy not active");
        require(_policies[policyId].tokenId == tokenId, "Policy token mismatch");

        _tokenGranteePolicy[tokenId][grantee] = policyId;
        _tokenGrantees[tokenId].push(grantee);

        emit AccessGranted(tokenId, grantee, policyId);
    }

    /**
     * @notice 撤销某地址对指定 tokenId 的访问权限
     * @param tokenId 资产 tokenId
     * @param grantee 被撤销地址
     */
    function revokeAccess(uint256 tokenId, address grantee) external override {
        require(_tokenGranteePolicy[tokenId][grantee] != 0, "No active access");

        // 使对应策略失效
        uint256 policyId = _tokenGranteePolicy[tokenId][grantee];
        _policies[policyId].isActive = false;

        // 清除授权映射
        delete _tokenGranteePolicy[tokenId][grantee];

        // 从 grantee 列表中移除
        address[] storage grantees = _tokenGrantees[tokenId];
        for (uint256 i = 0; i < grantees.length; i++) {
            if (grantees[i] == grantee) {
                grantees[i] = grantees[grantees.length - 1];
                grantees.pop();
                break;
            }
        }

        emit AccessRevoked(tokenId, grantee);
    }

    /**
     * @notice 检查某地址是否有权访问指定 tokenId
     * @param tokenId 资产 tokenId
     * @param account 待检查地址
     * @return 是否有权限
     */
    function checkAccess(uint256 tokenId, address account) external view override returns (bool) {
        uint256 policyId = _tokenGranteePolicy[tokenId][account];
        if (policyId == 0) {
            return false;
        }

        AccessPolicy memory policy = _policies[policyId];
        if (!policy.isActive) {
            return false;
        }

        // 检查过期
        if (policy.expiresAt != 0 && block.timestamp > policy.expiresAt) {
            return false;
        }

        return true;
    }

    /**
     * @notice 获取策略详情
     * @param policyId 策略 ID
     * @return 策略结构体
     */
    function getPolicy(uint256 policyId) external view override returns (AccessPolicy memory) {
        require(_policies[policyId].tokenId != 0 || policyId == 0, "Policy not found");
        return _policies[policyId];
    }

    /**
     * @notice 更新策略的访问级别和过期时间
     * @param policyId 策略 ID
     * @param accessLevel 新的访问级别
     * @param expiresAt 新的过期时间
     */
    function updatePolicy(uint256 policyId, uint8 accessLevel, uint256 expiresAt) external override {
        require(_policies[policyId].isActive, "Policy not active");
        require(accessLevel >= 1 && accessLevel <= 4, "Invalid access level");
        require(expiresAt == 0 || expiresAt > block.timestamp, "Invalid expiry");

        _policies[policyId].accessLevel = accessLevel;
        _policies[policyId].expiresAt = expiresAt;
    }

    /**
     * @notice 获取某 tokenId 的所有被授权地址
     * @param tokenId 资产 tokenId
     * @return 授权地址列表
     */
    function getGrantees(uint256 tokenId) external view returns (address[] memory) {
        return _tokenGrantees[tokenId];
    }

    /**
     * @notice 获取某地址被授权的策略 ID
     * @param tokenId 资产 tokenId
     * @param grantee 被授权地址
     * @return policyId 策略 ID（0 表示未授权）
     */
    function getGrantedPolicyId(uint256 tokenId, address grantee) external view returns (uint256) {
        return _tokenGranteePolicy[tokenId][grantee];
    }
}
