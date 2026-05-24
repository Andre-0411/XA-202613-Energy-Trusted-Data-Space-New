"""
联邦学习 API - /api/v1/compute/fl
FATE 集成：发起训练 / 模型管理 / 模型评估 / 任务管理 / 数据管理

增强端点:
- FATE 任务提交/查询/取消/列表
- 数据上传/下载
- SSE 训练进度推送
- 组件/算法列表
- 配置校验
- 连接状态
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import fl_service
from app.services import fate_integration

router = APIRouter()


# ==================== 联邦学习训练 (原有端点) ====================

@router.post("/train", response_model=ApiResponse)
async def submit_fl_training(
    name: str = Query(..., max_length=200, description="训练任务名称"),
    algorithm: str = Query(..., description="算法: lr/secureboost/nn/fm/svd/kmeans"),
    participants: str = Query(..., description="参与方DID（逗号分隔）"),
    dataset_config: str = Query(default="{}", description="数据集配置JSON"),
    model_params: Optional[str] = Query(default=None, description="模型参数JSON（可选）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    发起 FL 训练

    支持6种算法：lr(逻辑回归)/secureboost(安全提升树)/nn(神经网络)/fm(因子分解机)/svd/kmeans
    至少需要2个参与方
    """
    participant_list = [p.strip() for p in participants.split(",") if p.strip()]
    parsed_config = json.loads(dataset_config) if dataset_config else {}
    parsed_params = json.loads(model_params) if model_params else None
    result = await fl_service.submit_fl_training(
        db=db,
        name=name,
        algorithm=algorithm,
        participants=participant_list,
        dataset_config=parsed_config,
        model_params=parsed_params,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/models", response_model=ApiResponse)
async def list_models(
    algorithm: Optional[str] = Query(None, description="按算法筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """FL 模型列表"""
    result = await fl_service.list_models(
        db=db, algorithm=algorithm, status=status, limit=limit, offset=offset,
    )
    return ApiResponse(data=result)


@router.get("/models/{model_id}", response_model=ApiResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """FL 模型详情"""
    result = await fl_service.get_model(db=db, model_id=model_id)
    return ApiResponse(data=result)


@router.post("/models/{model_id}/evaluate", response_model=ApiResponse)
async def evaluate_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    模型评估

    计算精度/F1/AUC等指标（分类任务），RMSE/MAE（推荐任务），轮廓系数（聚类任务）
    """
    result = await fl_service.evaluate_model(db=db, model_id=model_id)
    return ApiResponse(data=result)


# ==================== FATE 任务管理 (新增端点) ====================

@router.post("/fate/jobs/submit", response_model=ApiResponse)
async def submit_fate_job(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    提交 FATE 联邦学习任务

    请求体为 FATE v2 DSL 格式配置:
    {
        "dsl_version": 2,
        "initiator": {"role": "guest", "party_id": 9999},
        "role": {"guest": [...], "host": [...]},
        "component_parameters": {...},
        "component_list": [...]
    }
    """
    body = await request.json()
    result = await fate_integration.submit_job(db=db, job_config=body)
    return ApiResponse(data=result)


@router.get("/fate/jobs/{job_id}", response_model=ApiResponse)
async def get_fate_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询 FATE 任务状态"""
    result = await fate_integration.get_job_status(db=db, job_id=job_id)
    return ApiResponse(data=result)


@router.get("/fate/jobs/{job_id}/result", response_model=ApiResponse)
async def get_fate_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 FATE 任务结果（模型参数、评估指标）"""
    result = await fate_integration.get_job_result(db=db, job_id=job_id)
    return ApiResponse(data=result)


@router.get("/fate/jobs/{job_id}/metrics", response_model=ApiResponse)
async def get_fate_job_metrics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 FATE 任务的模型评估指标"""
    result = await fate_integration.get_job_metrics(db=db, job_id=job_id)
    return ApiResponse(data=result)


@router.post("/fate/jobs/{job_id}/cancel", response_model=ApiResponse)
async def cancel_fate_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """取消 FATE 任务"""
    result = await fate_integration.cancel_job(db=db, job_id=job_id)
    return ApiResponse(data=result)


@router.get("/fate/jobs", response_model=ApiResponse)
async def list_fate_jobs(
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出所有 FATE 任务"""
    result = await fate_integration.list_jobs(db=db, limit=limit, offset=offset)
    return ApiResponse(data=result)


# ==================== SSE 训练进度推送 ====================

@router.get("/fate/jobs/{job_id}/progress")
async def stream_fate_job_progress(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """
    SSE 流式推送 FATE 任务训练进度

    事件格式:
    event: connected
    data: {"job_id": "..."}

    event: progress
    data: {"step": 1, "progress": 10, ...}

    event: status_change
    data: {"status": "completed", ...}

    : heartbeat
    """
    async def event_stream():
        async for event in fate_integration.progress_event_generator(job_id):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 数据管理 ====================

@router.post("/fate/data/upload", response_model=ApiResponse)
async def upload_fate_data(
    table_name: str = Query(..., description="表名"),
    file_path: str = Query(..., description="本地文件路径"),
    namespace: str = Query("default", description="命名空间"),
    party_id: Optional[int] = Query(None, description="参与方 ID"),
    user: dict = Depends(get_current_user),
):
    """上传数据集到 FATE Flow"""
    result = await fate_integration.upload_data(
        table_name=table_name,
        file_path=file_path,
        namespace=namespace,
        party_id=party_id,
    )
    return ApiResponse(data=result)


@router.get("/fate/data/download", response_model=ApiResponse)
async def download_fate_data(
    table_name: str = Query(..., description="表名"),
    namespace: str = Query("default", description="命名空间"),
    output_path: Optional[str] = Query(None, description="输出文件路径"),
    user: dict = Depends(get_current_user),
):
    """从 FATE Flow 下载数据集"""
    result = await fate_integration.download_data(
        table_name=table_name,
        namespace=namespace,
        output_path=output_path,
    )
    return ApiResponse(data=result)


# ==================== 配置校验 ====================

@router.post("/fate/config/validate", response_model=ApiResponse)
async def validate_fate_config(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    校验 FATE v2 DSL 任务配置

    请求体为 FATE v2 DSL 配置 JSON
    """
    body = await request.json()
    result = fate_integration.validate_fate_config(job_config=body)
    return ApiResponse(data=result)


# ==================== 元数据查询 ====================

@router.get("/fate/algorithms", response_model=ApiResponse)
async def get_supported_algorithms(
    user: dict = Depends(get_current_user),
):
    """获取 FATE 支持的算法列表"""
    result = fate_integration.get_supported_algorithms()
    return ApiResponse(data=result)


@router.get("/fate/components", response_model=ApiResponse)
async def get_supported_components(
    user: dict = Depends(get_current_user),
):
    """获取 FATE 支持的组件列表及参数定义"""
    result = fate_integration.get_supported_components()
    return ApiResponse(data=result)


@router.get("/fate/connection", response_model=ApiResponse)
async def get_fate_connection_status(
    user: dict = Depends(get_current_user),
):
    """获取 FATE Flow 连接状态和指标"""
    result = fate_integration.get_connection_status()
    return ApiResponse(data=result)


# ==================== 任务模板 ====================

@router.post("/fate/templates/homo-lr", response_model=ApiResponse)
async def generate_homo_lr_template(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    生成横向联邦学习任务配置模板

    请求体:
    {
        "parties": [{"role": "guest", "party_id": 9999}, {"role": "host", "party_id": 10000}],
        "dataset": "energy_data",
        "epochs": 10,
        "learning_rate": 0.1
    }
    """
    body = await request.json()
    result = fate_integration.generate_homo_lr_config(
        parties=body.get("parties", []),
        dataset=body.get("dataset", ""),
        epochs=body.get("epochs", 10),
        learning_rate=body.get("learning_rate", 0.1),
    )
    return ApiResponse(data=result)


@router.post("/fate/templates/hetero-lr", response_model=ApiResponse)
async def generate_hetero_lr_template(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    生成纵向联邦学习任务配置模板

    请求体:
    {
        "guest_party_id": 9999,
        "host_party_ids": [10000, 10001],
        "guest_dataset": "energy_data_guest",
        "host_datasets": ["energy_data_host1", "energy_data_host2"],
        "epochs": 10
    }
    """
    body = await request.json()
    result = fate_integration.generate_hetero_lr_config(
        guest_party_id=body.get("guest_party_id", 9999),
        host_party_ids=body.get("host_party_ids", []),
        guest_dataset=body.get("guest_dataset", ""),
        host_datasets=body.get("host_datasets", []),
        epochs=body.get("epochs", 10),
    )
    return ApiResponse(data=result)


@router.post("/fate/templates/psi", response_model=ApiResponse)
async def generate_psi_template(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    生成隐私集合求交任务配置模板

    请求体:
    {
        "parties": [{"role": "guest", "party_id": 9999}, {"role": "host", "party_id": 10000}],
        "datasets": ["dataset_guest", "dataset_host"]
    }
    """
    body = await request.json()
    result = fate_integration.generate_psi_config(
        parties=body.get("parties", []),
        datasets=body.get("datasets", []),
    )
    return ApiResponse(data=result)
