"""
安全多方计算 API - /api/v1/compute/mpc
MP-SPDZ 集成：发起MPC计算 / 会话管理 / DAG编排 / 安全运算

增强端点:
- 会话管理: 创建/加入/执行/结果获取
- DAG 计算任务编排
- 安全加法/安全乘法
- 会话状态查询
- 结果验证
"""
import json
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import mpc_service

router = APIRouter()


# ==================== MPC 计算 (原有端点) ====================

@router.post("/compute", response_model=ApiResponse)
async def submit_mpc_computation(
    name: str = Query(..., max_length=200, description="计算任务名称"),
    protocol: str = Query(..., description="MPC协议: spdz/psn/aby3/falcon/chaiguru/malicious-sha2"),
    participants: str = Query(..., description="参与方DID（逗号分隔）"),
    computation_config: str = Query(default="{}", description="计算配置JSON（含circuit或function定义）"),
    input_asset_ids: Optional[str] = Query(None, description="输入资产ID（逗号分隔）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    发起 MPC 安全多方计算

    协议说明:
    - spdz: 恶意安全算术协议（2-10方）
    - psn: 半诚实算术协议（2-10方）
    - aby3: 混合协议（严格3方）
    - falcon: 恶意安全三方协议（严格3方）
    - chaiguru: 混淆电路两方协议（严格2方）
    """
    participant_list = [p.strip() for p in participants.split(",") if p.strip()]
    asset_id_list = []
    if input_asset_ids:
        asset_id_list = [a.strip() for a in input_asset_ids.split(",") if a.strip()]

    parsed_config = json.loads(computation_config) if computation_config else {}

    result = await mpc_service.submit_mpc_computation(
        db=db,
        name=name,
        protocol=protocol,
        participants=participant_list,
        computation_config=parsed_config,
        input_asset_ids=asset_id_list,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/protocols", response_model=ApiResponse)
async def list_protocols():
    """查询可用的 MPC 协议列表"""
    result = await mpc_service.list_protocols()
    return ApiResponse(data=result)


# ==================== 会话管理 (新增端点) ====================

@router.post("/sessions/create", response_model=ApiResponse)
async def create_mpc_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建 MPC 计算会话

    请求体:
    {
        "name": "能源数据聚合计算",
        "protocol": "spdz",
        "participants": ["party_a", "party_b"],
        "computation_config": {"function": "secure_sum", "inputs": [...]},
        "input_asset_ids": ["asset_1", "asset_2"]
    }
    """
    body = await request.json()
    result = await mpc_service.create_mpc_session(
        db=db,
        name=body.get("name", ""),
        protocol=body.get("protocol", "spdz"),
        participants=body.get("participants", []),
        computation_config=body.get("computation_config", {}),
        input_asset_ids=body.get("input_asset_ids"),
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.post("/sessions/{session_id}/join", response_model=ApiResponse)
async def join_mpc_session(
    session_id: str,
    party_id: str = Query(..., description="参与方 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """参与方加入 MPC 会话"""
    result = await mpc_service.join_session(
        db=db,
        session_id=session_id,
        party_id=party_id,
    )
    return ApiResponse(data=result)


@router.post("/sessions/{session_id}/execute", response_model=ApiResponse)
async def execute_mpc_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 MPC 会话（启动在线阶段计算）"""
    result = await mpc_service.execute_session(
        db=db,
        session_id=session_id,
    )
    return ApiResponse(data=result)


@router.get("/sessions/{session_id}/result", response_model=ApiResponse)
async def get_mpc_session_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 MPC 会话计算结果"""
    result = await mpc_service.get_session_result(
        db=db,
        session_id=session_id,
    )
    return ApiResponse(data=result)


@router.get("/sessions/{session_id}/status", response_model=ApiResponse)
async def get_mpc_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询 MPC 会话状态（含 SPDZ 协议详情和任务进度）"""
    result = await mpc_service.get_session_status(
        db=db,
        session_id=session_id,
    )
    return ApiResponse(data=result)


# ==================== DAG 计算编排 (新增端点) ====================

@router.post("/dag/create", response_model=ApiResponse)
async def create_dag_computation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建 DAG 格式的 MPC 计算任务编排

    请求体:
    {
        "name": "能源数据多阶段计算",
        "protocol": "spdz",
        "participants": ["party_a", "party_b"],
        "dag_definition": {
            "nodes": [
                {"id": "n1", "type": "input", "params": {"asset_id": "xxx"}},
                {"id": "n2", "type": "compute", "op": "add", "inputs": ["n1", "n3"]},
                {"id": "n3", "type": "input", "params": {"asset_id": "yyy"}},
                {"id": "n4", "type": "output", "inputs": ["n2"]}
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n3", "to": "n2"},
                {"from": "n2", "to": "n4"}
            ]
        }
    }
    """
    body = await request.json()
    result = await mpc_service.create_dag_computation(
        db=db,
        name=body.get("name", ""),
        protocol=body.get("protocol", "spdz"),
        participants=body.get("participants", []),
        dag_definition=body.get("dag_definition", {}),
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


# ==================== 安全运算接口 (新增端点) ====================

@router.post("/sessions/{session_id}/secure-add", response_model=ApiResponse)
async def secure_add(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    在 MPC 会话中执行安全加法

    请求体:
    {
        "values": [100, 200, 300]
    }

    各方的值通过加法秘密共享拆分，本地相加后恢复结果。
    """
    body = await request.json()
    values = body.get("values", [])
    result = await mpc_service.secure_add_values(
        db=db,
        session_id=session_id,
        values=values,
    )
    return ApiResponse(data=result)


@router.post("/sessions/{session_id}/secure-multiply", response_model=ApiResponse)
async def secure_multiply(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    在 MPC 会话中执行安全乘法（SPDZ 协议）

    请求体:
    {
        "values": [42, 58]
    }

    使用 Beaver 三元组实现安全乘法，仅需两方参与。
    """
    body = await request.json()
    values = body.get("values", [])
    result = await mpc_service.secure_multiply_values(
        db=db,
        session_id=session_id,
        values=values,
    )
    return ApiResponse(data=result)


# ==================== 结果验证 (新增端点) ====================

@router.post("/verify", response_model=ApiResponse)
async def verify_mpc_result(
    task_id: str = Query(..., description="任务 ID"),
    result_hash: str = Query(..., description="待验证的结果哈希"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    验证 MPC 计算结果的完整性

    比对任务存储的结果哈希与传入的哈希是否一致
    """
    result = await mpc_service.verify_mpc_result(
        db=db,
        task_id=task_id,
        result_hash=result_hash,
    )
    return ApiResponse(data=result)
