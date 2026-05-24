// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAccessControl {
    struct AccessPolicy {
        uint256 tokenId;
        uint8 accessLevel;    // 1:只读, 2:计算, 3:导出, 4:管理
        uint256 expiresAt;
        string conditions;    // JSON 格式的附加条件
        bool isActive;
    }

    event AccessGranted(uint256 tokenId, address grantee, uint256 policyId);
    event AccessRevoked(uint256 tokenId, address grantee);
    event PolicyCreated(uint256 policyId, uint256 tokenId);

    function createPolicy(uint256 tokenId, uint8 accessLevel, uint256 expiresAt, string calldata conditions) external returns (uint256);
    function grantAccess(uint256 tokenId, address grantee, uint256 policyId) external;
    function revokeAccess(uint256 tokenId, address grantee) external;
    function checkAccess(uint256 tokenId, address account) external view returns (bool);
    function getPolicy(uint256 policyId) external view returns (AccessPolicy memory);
    function updatePolicy(uint256 policyId, uint8 accessLevel, uint256 expiresAt) external;
}
