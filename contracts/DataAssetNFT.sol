// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IDataAssetNFT.sol";
import "./interfaces/IIdentityRegistry.sol";

/**
 * @title DataAssetNFT
 * @notice 数据资产 NFT 化合约 - 将能源数据资产铸造为链上 NFT
 * @dev 实现 IDataAssetNFT 接口，关联身份注册中心进行铸造权限校验
 */
contract DataAssetNFT is IDataAssetNFT {
    /// @notice 身份注册中心合约
    IIdentityRegistry public identityRegistry;

    /// @notice 合约管理员
    address public admin;

    /// @notice tokenId 计数器
    uint256 private _tokenIdCounter;

    /// @notice tokenId => 资产元数据
    mapping(uint256 => AssetMetadata) private _tokenMetadata;

    /// @notice tokenId => 所有者地址
    mapping(uint256 => address) private _tokenOwner;

    /// @notice assetId => tokenId（资产唯一映射）
    mapping(string => uint256) private _assetToToken;

    /// @notice 地址 => 拥有的 tokenId 列表
    mapping(address => uint256[]) private _ownerTokens;

    /// @notice 构造函数
    /// @param _identityRegistry 身份注册中心地址
    constructor(address _identityRegistry) {
        identityRegistry = IIdentityRegistry(_identityRegistry);
        admin = msg.sender;
    }

    /**
     * @notice 铸造数据资产 NFT
     * @param to 接收者地址
     * @param assetId 资产唯一标识
     * @param category 数据分类（发电/用电/调度/市场/设备/地理）
     * @param level 分类等级：1=核心, 2=重要, 3=一般, 4=公开
     * @param evidenceHash 存证哈希
     * @param certificateURI 证书 URI（IPFS/HTTP）
     * @return tokenId 铸造的 tokenId
     */
    function mint(
        address to,
        string calldata assetId,
        string calldata category,
        uint8 level,
        bytes32 evidenceHash,
        string calldata certificateURI
    ) external override returns (uint256) {
        require(to != address(0), "Invalid recipient");
        require(bytes(assetId).length > 0, "Asset ID required");
        require(level >= 1 && level <= 4, "Invalid classification level");
        require(bytes(certificateURI).length > 0, "Certificate URI required");
        require(_assetToToken[assetId] == 0, "Asset already minted");

        _tokenIdCounter++;
        uint256 tokenId = _tokenIdCounter;

        _tokenMetadata[tokenId] = AssetMetadata({
            assetId: assetId,
            category: category,
            classificationLevel: level,
            evidenceHash: evidenceHash,
            certificateURI: certificateURI,
            mintedAt: block.timestamp
        });

        _tokenOwner[tokenId] = to;
        _assetToToken[assetId] = tokenId;
        _ownerTokens[to].push(tokenId);

        emit AssetMinted(tokenId, assetId, category, level);
        return tokenId;
    }

    /**
     * @notice 销毁数据资产 NFT
     * @param tokenId 要销毁的 tokenId
     */
    function burn(uint256 tokenId) external override {
        require(_tokenOwner[tokenId] != address(0), "Token does not exist");
        require(
            _tokenOwner[tokenId] == msg.sender || msg.sender == admin,
            "Not authorized"
        );

        string memory assetId = _tokenMetadata[tokenId].assetId;

        // 清理映射
        delete _assetToToken[assetId];
        delete _tokenMetadata[tokenId];

        address owner = _tokenOwner[tokenId];
        delete _tokenOwner[tokenId];

        // 从 ownerTokens 中移除
        uint256[] storage tokens = _ownerTokens[owner];
        for (uint256 i = 0; i < tokens.length; i++) {
            if (tokens[i] == tokenId) {
                tokens[i] = tokens[tokens.length - 1];
                tokens.pop();
                break;
            }
        }

        emit AssetBurned(tokenId);
    }

    /**
     * @notice 获取资产元数据
     * @param tokenId tokenId
     * @return 元数据结构体
     */
    function getAssetMetadata(uint256 tokenId) external view override returns (AssetMetadata memory) {
        require(_tokenOwner[tokenId] != address(0), "Token does not exist");
        return _tokenMetadata[tokenId];
    }

    /**
     * @notice 更新证书 URI（仅所有者或管理员）
     * @param tokenId tokenId
     * @param certificateURI 新的证书 URI
     */
    function updateMetadata(uint256 tokenId, string calldata certificateURI) external override {
        require(_tokenOwner[tokenId] != address(0), "Token does not exist");
        require(
            _tokenOwner[tokenId] == msg.sender || msg.sender == admin,
            "Not authorized"
        );
        require(bytes(certificateURI).length > 0, "URI cannot be empty");

        _tokenMetadata[tokenId].certificateURI = certificateURI;
    }

    /**
     * @notice 根据资产 ID 获取 tokenId
     * @param assetId 资产唯一标识
     * @return tokenId
     */
    function tokenOfAsset(string calldata assetId) external view override returns (uint256) {
        uint256 tokenId = _assetToToken[assetId];
        require(tokenId != 0, "Asset not found");
        return tokenId;
    }

    /**
     * @notice 检查资产是否存在
     * @param assetId 资产唯一标识
     * @return 是否存在
     */
    function exists(string calldata assetId) external view override returns (bool) {
        return _assetToToken[assetId] != 0;
    }

    /**
     * @notice 获取 tokenId 的所有者地址
     * @param tokenId tokenId
     * @return owner 所有者地址
     */
    function ownerOf(uint256 tokenId) external view returns (address) {
        require(_tokenOwner[tokenId] != address(0), "Token does not exist");
        return _tokenOwner[tokenId];
    }

    /**
     * @notice 获取某地址拥有的所有 tokenId
     * @param owner 所有者地址
     * @return tokenId 列表
     */
    function tokensOfOwner(address owner) external view returns (uint256[] memory) {
        return _ownerTokens[owner];
    }

    /**
     * @notice 获取已铸造的总 token 数量
     * @return 总数
     */
    function totalSupply() external view returns (uint256) {
        return _tokenIdCounter;
    }
}
