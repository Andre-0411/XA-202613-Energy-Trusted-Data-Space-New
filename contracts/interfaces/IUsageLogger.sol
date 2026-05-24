// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IUsageLogger {
    struct UsageRecord {
        bytes32 recordId;
        string nodeType;      // collect/preprocess/classify/publish/apply/compute/result/settle
        string resourceId;
        string resourceType;
        bytes32 dataHash;
        bytes evidenceData;
        bytes32 prevHash;     // 链式哈希，形成证据链
        address operator;
        uint256 timestamp;
        bool isValid;
    }

    event UsageLogged(bytes32 recordId, string nodeType, string resourceId, bytes32 dataHash, bytes32 prevHash, uint256 timestamp);

    function logUsage(string calldata nodeType, string calldata resourceId, string calldata resourceType, bytes32 dataHash, bytes calldata evidenceData) external returns (bytes32);
    function verifyRecord(bytes32 recordId) external view returns (bool);
    function getRecord(bytes32 recordId) external view returns (UsageRecord memory);
    function getRecordsByResource(string calldata resourceId) external view returns (bytes32[] memory);
    function getRecordCount() external view returns (uint256);
    function getLastHash() external view returns (bytes32);
}
