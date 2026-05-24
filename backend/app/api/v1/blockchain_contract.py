"""
智能合约 API — /api/v1/blockchain/contracts
合约列表 / 交易记录 / 合约详情 / 合约调用 / 链状态 / 合约部署

路由注册顺序（精确路径优先于参数化路径）：
  1. GET  /chain/status               → 链状态（公开）
  2. GET  /                           → 合约列表（公开）
  3. POST /deploy                     → 部署单个合约（需认证，admin）
  4. POST /deploy-all                 → 一键部署全部（需认证，admin）
  5. GET  /transactions               → 全局交易记录（需认证）
  6. GET  /{id}/transactions          → 合约交易记录（需认证）
  7. GET  /{id}                       → 合约详情（需认证）
  8. POST /{id}/invoke                → 合约调用（需认证）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.blockchain import ContractCallRequest
from app.utils.deps import get_current_user
from app.services.blockchain_contract_service import (
    call_contract, send_transaction, list_transactions,
)
from app.services.blockchain_chain_service import get_blockchain_chain_service
from app.exceptions import SmartContractError

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 1. GET /chain/status — 链状态（公开访问，无需认证）
# ============================================================
@router.get("/chain/status", response_model=ApiResponse)
async def 链状态():
    """
    链状态 — 区块高度、节点数、连接状态

    公开端点，不需要认证。
    """
    try:
        chain_service = get_blockchain_chain_service()
        chain_info = await chain_service.get_chain_status()
        return ApiResponse(data=chain_info)
    except Exception as e:
        logger.error(f"Chain status query failed: {e}")
        return ApiResponse(
            code=5000,
            message=f"查询链状态失败: {e}",
            data={
                'connected': False,
                'block_number': 0,
                'peer_count': 0,
                'chain_id': 0,
                'latest_block_time': 0,
            },
        )


# ============================================================
# 2. GET / — 合约列表（公开访问，无需认证）
# ============================================================
@router.get("/", response_model=ApiResponse)
async def 合约列表():
    """
    合约列表 — 从 ContractRegistry 读取真实已部署合约

    如果注册中心为空则返回空列表。
    每个合约返回: name, address, version, status, deployed_at, deploy_tx_hash
    """
    try:
        chain_service = get_blockchain_chain_service()
        deployment_status = await chain_service.get_deployment_status()
        contracts_raw = deployment_status.get('contracts', {})

        contracts = []
        for name, info in contracts_raw.items():
            contracts.append({
                'name': name,
                'address': info.get('address', ''),
                'version': info.get('version', ''),
                'status': info.get('status', ''),
                'deployed_at': info.get('deployed_at', ''),
                'deploy_tx_hash': info.get('deploy_tx_hash', ''),
            })

        return ApiResponse(data=contracts)
    except Exception as e:
        logger.error(f"Contract list query failed: {e}")
        return ApiResponse(data=[])


# ============================================================
# 3. POST /deploy — 部署单个合约（需认证，admin 角色）
# ============================================================
@router.post("/deploy", response_model=ApiResponse)
async def 部署合约(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    部署单个合约

    Body: { "contract_name": "...", "account": "..."? }

    支持的合约名: IdentityRegistry, DataAssetNFT, AccessControl,
                  UsageLogger, AutoSettlement, ComplianceAudit

    仅 admin 角色可执行部署。
    """
    # 权限检查 — 仅 admin 可部署
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 1006, "message": "仅管理员可执行合约部署"},
        )

    contract_name: str = body.get("contract_name", "")
    account: Optional[str] = body.get("account")

    if not contract_name:
        return ApiResponse(code=2003, message="contract_name 为必填项", data=None)

    try:
        chain_service = get_blockchain_chain_service()
        result = await chain_service.deploy_contract(contract_name, account)
        return ApiResponse(data=result)
    except ValueError as e:
        logger.warning(f"Deploy validation failed: {e}")
        return ApiResponse(code=2003, message=str(e), data=None)
    except FileNotFoundError as e:
        logger.error(f"Deploy artifact not found: {e}")
        return ApiResponse(code=4040, message=f"编译产物未找到，请先编译合约: {e}", data=None)
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        return ApiResponse(code=5000, message=f"合约部署失败: {e}", data=None)


# ============================================================
# 4. POST /deploy-all — 一键部署全部（需认证，admin 角色）
# ============================================================
@router.post("/deploy-all", response_model=ApiResponse)
async def 一键部署全部(
    user: dict = Depends(get_current_user),
):
    """
    一键部署所有合约（按依赖顺序）

    仅 admin 角色可执行。
    部署顺序: IdentityRegistry → DataAssetNFT → AccessControl / UsageLogger / AutoSettlement → ComplianceAudit
    """
    # 权限检查 — 仅 admin 可部署
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 1006, "message": "仅管理员可执行合约部署"},
        )

    try:
        chain_service = get_blockchain_chain_service()
        result = await chain_service.deploy_all_contracts()
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Deploy all failed: {e}")
        return ApiResponse(code=5000, message=f"一键部署失败: {e}", data=None)


# ============================================================
# 5. GET /transactions — 全局交易记录（必须在 /{id} 之前注册）
# ============================================================
@router.get("/transactions", response_model=ApiResponse)
async def 交易记录(
    contract_address: Optional[str] = Query(None, description="合约地址"),
    method: Optional[str] = Query(None, description="方法名"),
    status: Optional[str] = Query(None, description="交易状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """交易记录 — 按合约地址/方法/状态筛选，分页"""
    offset: int = (page - 1) * page_size

    try:
        result = await list_transactions(
            db=db,
            contract_address=contract_address,
            method=method,
            status=status,
            limit=page_size,
            offset=offset,
        )
        total: int = result.get("total", 0)
        total_pages: int = (total + page_size - 1) // page_size if page_size > 0 else 0
        return ApiResponse(data={
            "items": result.get("items", []),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        })
    except Exception as e:
        logger.error(f"Transaction list failed: {e}")
        return ApiResponse(code=4000, message=f"查询交易记录失败: {e}", data=None)


# ============================================================
# 6. GET /{id}/transactions — 合约交易记录（必须在 /{id} 之前注册）
# ============================================================
@router.get("/{id}/transactions", response_model=ApiResponse)
async def 合约交易记录(
    id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """按合约ID查询交易记录 — 前端 GET /blockchain/contracts/{id}/transactions"""
    offset: int = (page - 1) * page_size

    try:
        result = await list_transactions(
            db=db,
            contract_address=id,
            limit=page_size,
            offset=offset,
        )
        total: int = result.get("total", 0)
        total_pages: int = (total + page_size - 1) // page_size if page_size > 0 else 0
        return ApiResponse(data={
            "items": result.get("items", []),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        })
    except Exception as e:
        logger.error(f"Contract transaction list failed: {e}")
        return ApiResponse(code=4000, message=f"查询合约交易记录失败: {e}", data=None)


# ============================================================
# 7. GET /{id} — 合约详情+ABI（必须在所有精确路由之后注册）
# ============================================================
@router.get("/{id}", response_model=ApiResponse)
async def 合约详情_abi(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """合约详情+ABI — 按合约ID查询"""
    # 先从 ContractRegistry 查找真实合约
    from app.core.contract_registry import get_contract_registry
    registry = get_contract_registry()
    contract = registry.get_contract(id)

    if contract:
        return ApiResponse(data={
            'name': contract.name,
            'address': contract.address,
            'version': contract.version,
            'status': contract.status,
            'deployed_at': contract.deployed_at,
            'deploy_tx_hash': contract.deploy_tx_hash,
            'abi': contract.abi,
            'transactions_count': 0,
        })

    # 回退到按地址查找
    for c in registry.get_all():
        if c.address == id:
            return ApiResponse(data={
                'name': c.name,
                'address': c.address,
                'version': c.version,
                'status': c.status,
                'deployed_at': c.deployed_at,
                'deploy_tx_hash': c.deploy_tx_hash,
                'abi': c.abi,
                'transactions_count': 0,
            })

    # 未找到已知合约，返回基础信息
    return ApiResponse(data={
        "address": id,
        "name": id,
        "description": "未知合约",
        "abi": [],
        "transactions_count": 0,
        "created_at": None,
    })


# ============================================================
# 8. POST /{id}/invoke — 合约调用
# ============================================================
@router.post("/{id}/invoke", response_model=ApiResponse)
async def 调用合约方法(
    id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """调用合约方法 — 前端 POST /blockchain/contracts/{id}/invoke {method, args}"""
    user_did: str = user.get("user_id", "")
    method: str = body.get("method", "")
    args: dict = body.get("args") or {}

    if not method:
        return ApiResponse(code=2003, message="method 为必填项", data=None)

    call_request = ContractCallRequest(
        method=method,
        params=args,
        from_address=id,
    )

    try:
        # 根据方法名判断是读操作还是写操作
        write_keywords = ("send", "settle", "transfer", "mint", "deploy", "burn", "approve")
        is_write = method.lower().startswith(write_keywords) or any(
            kw in method.lower() for kw in write_keywords
        )

        if is_write:
            result = await send_transaction(
                db=db, request=call_request, user_did=user_did,
            )
        else:
            result = await call_contract(db=db, request=call_request)

        return ApiResponse(data=result)
    except SmartContractError as e:
        logger.error(f"Contract call failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"Contract call failed: {e}")
        return ApiResponse(code=4010, message=f"合约调用失败: {e}", data=None)


# ============================================================
# 9. GET /block/{block_number} — 区块详情
# ============================================================
@router.get("/block/{block_number}", response_model=ApiResponse)
async def get_block_detail(
    block_number: int,
    user: dict = Depends(get_current_user),
):
    """获取区块详情"""
    try:
        chain_service = get_blockchain_chain_service()
        block_info = await chain_service.get_block_info(block_number)
        return ApiResponse(data=block_info)
    except Exception as e:
        logger.error(f"Get block detail failed: {e}")
        return ApiResponse(code=5000, message=f"获取区块详情失败: {e}", data=None)


# ============================================================
# 10. GET /transaction/{tx_hash} — 交易详情
# ============================================================
@router.get("/transaction/{tx_hash}", response_model=ApiResponse)
async def get_transaction_detail(
    tx_hash: str,
    user: dict = Depends(get_current_user),
):
    """获取交易详情"""
    try:
        chain_service = get_blockchain_chain_service()
        tx_info = await chain_service.get_transaction_info(tx_hash)
        return ApiResponse(data=tx_info)
    except Exception as e:
        logger.error(f"Get transaction detail failed: {e}")
        return ApiResponse(code=5000, message=f"获取交易详情失败: {e}", data=None)


# ============================================================
# 11. GET /fisco/status — FISCO BCOS 连接状态
# ============================================================
@router.get("/fisco/status", response_model=ApiResponse)
async def get_fisco_connection_status(
    user: dict = Depends(get_current_user),
):
    """获取 FISCO BCOS 连接状态"""
    try:
        chain_service = get_blockchain_chain_service()
        status_info = await chain_service.get_connection_status()
        return ApiResponse(data=status_info)
    except Exception as e:
        logger.error(f"Get FISCO status failed: {e}")
        return ApiResponse(data={
            "connected": False,
            "current_node": "unknown",
            "block_number": 0,
            "peer_count": 0,
            "chain_id": "unknown",
            "group_id": 1,
            "stats": {},
        })


# ============================================================
# 12. GET /fisco/consensus — 共识状态
# ============================================================
@router.get("/fisco/consensus", response_model=ApiResponse)
async def get_consensus_status(
    user: dict = Depends(get_current_user),
):
    """获取共识状态"""
    try:
        chain_service = get_blockchain_chain_service()
        consensus_info = await chain_service.get_consensus_status()
        return ApiResponse(data=consensus_info)
    except Exception as e:
        logger.error(f"Get consensus status failed: {e}")
        return ApiResponse(data={
            "connected": False,
            "consensus_nodes": [],
            "view": 0,
            "leader": "unknown",
        })


# ============================================================
# 13. GET /fisco/sync — 同步状态
# ============================================================
@router.get("/fisco/sync", response_model=ApiResponse)
async def get_sync_status(
    user: dict = Depends(get_current_user),
):
    """获取同步状态"""
    try:
        chain_service = get_blockchain_chain_service()
        sync_info = await chain_service.get_sync_status()
        return ApiResponse(data=sync_info)
    except Exception as e:
        logger.error(f"Get sync status failed: {e}")
        return ApiResponse(data={
            "connected": False,
            "is_syncing": False,
            "current_block": 0,
            "highest_block": 0,
            "peers": [],
        })
