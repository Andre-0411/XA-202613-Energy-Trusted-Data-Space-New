// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IDataAssetNFT {
    struct AssetMetadata {
        string assetId;
        string category;      // 发电/用电/调度/市场/设备/地理
        uint8 classificationLevel;  // 1:核心, 2:重要, 3:一般, 4:公开
        bytes32 evidenceHash;
        string certificateURI;
        uint256 mintedAt;
    }

    event AssetMinted(uint256 tokenId, string assetId, string category, uint8 level);
    event AssetBurned(uint256 tokenId);

    function mint(address to, string calldata assetId, string calldata category, uint8 level, bytes32 evidenceHash, string calldata certificateURI) external returns (uint256);
    function burn(uint256 tokenId) external;
    function getAssetMetadata(uint256 tokenId) external view returns (AssetMetadata memory);
    function updateMetadata(uint256 tokenId, string calldata certificateURI) external;
    function tokenOfAsset(string calldata assetId) external view returns (uint256);
    function exists(string calldata assetId) external view returns (bool);
}
