// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IIdentityRegistry {
    struct Identity {
        string did;
        string publicKey;
        uint8 role;           // 0:普通用户, 1:数据提供方, 2:数据使用方, 3:监管方, 4:平台管理员
        bool isActive;
        uint256 registeredAt;
        uint256 updatedAt;
    }

    event IdentityRegistered(string did, address addr, uint8 role);
    event IdentityRevoked(string did);

    function registerIdentity(string calldata did, string calldata publicKey, uint8 role) external;
    function revokeIdentity(string calldata did) external;
    function verifyIdentity(string calldata did) external view returns (bool);
    function getIdentity(string calldata did) external view returns (Identity memory);
    function updatePublicKey(string calldata did, string calldata newPublicKey) external;
    function isRegistered(string calldata did) external view returns (bool);
    function transferAdmin(address newAdmin) external;
}
