"""
TEE API - /api/v1/compute/tee
Gramine TEE 集成：TEE内执行 / 实例状态 / 远程证明 / 实例销毁 / 列表查询

增强端点:
- 远程证明 (RA) 验证
- TEE 实例销毁
- TEE 实例列表
- TEE 运行时信息
"""
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import tee_service

router = APIRouter()


@router.post("/execute", response_model=ApiResponse)
async def execute_in_tee(
    name: str = Query(..., max_length=200, description="任务名称"),
    runtime: str = Query(..., description="TEE运行时: gramine/sgx/trustzone/tdx/sev"),
    code_ref: str = Query(..., description="代码引用（URI）"),
    input_data_refs: str = Query("", description="输入数据引用（逗号分隔）"),
    enclave_template: str = Query(
        "data_analysis",
        description="安全区模板: data_analysis/model_training/data_join/high_security"
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    TEE 内执行（增强版）

    在可信执行环境内安全执行代码，数据不离开安全区。

    增强:
    - SGX Enclave 代码签名验证 (MRENCLAVE/MRSIGNER)
    - 远程证明 (RA) 自动执行
    - TEE 沙箱（syscall 白名单、内存隔离）
    - 结果加密传输

    支持运行时: gramine(Gramine), sgx(Intel SGX), trustzone(ARM TrustZone), tdx(Intel TDX), sev(AMD SEV)
    安全区模板: data_analysis(数据分析), model_training(模型训练), data_join(数据连接), high_security(高安全区)
    """
    data_refs = [r.strip() for r in input_data_refs.split(",") if r.strip()]
    enclave_config = {"template": enclave_template}

    result = await tee_service.execute_in_tee(
        db=db,
        name=name,
        runtime=runtime,
        code_ref=code_ref,
        input_data_refs=data_refs,
        enclave_config=enclave_config,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/status/{instance_id}", response_model=ApiResponse)
async def get_tee_status(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    TEE 实例状态（增强版）

    查询安全区运行状态、MRENCLAVE、MRSIGNER、远程证明状态、沙箱状态、任务进度
    """
    result = await tee_service.get_tee_status(
        db=db,
        instance_id=instance_id,
    )
    return ApiResponse(data=result)


@router.post("/attest/{instance_id}", response_model=ApiResponse)
async def verify_remote_attestation(
    instance_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    远程证明 (Remote Attestation) 验证

    请求体:
    {
        "quote": "<SGX Quote (base64 或 JSON)>",
        "nonce": "<防重放随机数>"
    }

    验证内容:
    - Quote 签名有效性
    - MRENCLAVE 匹配（代码完整性）
    - MRSIGNER 匹配（签名者可信度）
    - TCB 状态
    """
    body = await request.json()
    quote = body.get("quote", "")
    nonce = body.get("nonce", "")

    result = await tee_service.verify_remote_attestation(
        db=db,
        instance_id=instance_id,
        quote=quote,
        nonce=nonce,
    )
    return ApiResponse(data=result)


@router.post("/destroy/{instance_id}", response_model=ApiResponse)
async def destroy_tee_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    销毁 TEE 实例

    清理:
    - 安全内存清零 (EPC 页面)
    - 沙箱关闭
    - 会话密钥销毁
    - 所有密态数据清除
    """
    result = await tee_service.destroy_tee_instance(
        db=db,
        instance_id=instance_id,
    )
    return ApiResponse(data=result)


@router.get("/instances", response_model=ApiResponse)
async def list_tee_instances(
    status: Optional[str] = Query(None, description="按状态筛选: creating/attesting/running/completed/failed/destroyed"),
    runtime: Optional[str] = Query(None, description="按运行时筛选: gramine/sgx/trustzone/tdx/sev"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 TEE 实例"""
    result = await tee_service.list_tee_instances(
        db=db,
        status=status,
        runtime=runtime,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.get("/runtime-info", response_model=ApiResponse)
async def get_tee_runtime_info(
    user: dict = Depends(get_current_user),
):
    """
    获取 TEE 运行时信息

    包含: 支持的运行时、安全区模板、签名方案、内存限制等
    """
    result = tee_service.get_tee_runtime_info()
    return ApiResponse(data=result)
