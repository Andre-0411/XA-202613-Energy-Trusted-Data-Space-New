"""
计算增强 API — /api/v1/compute/enhanced
FATE 联邦学习任务管理 / 计算沙箱 / DAG 编排增强 / 隐私计算路由
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.compute import DagCreate
from app.utils.deps import get_current_user
from app.services import fate_integration, compute_sandbox, dag_engine, privacy_router

router = APIRouter()


# ==================== FATE 联邦学习任务 ====================

@router.post("/fate/submit", response_model=ApiResponse, summary="提交FATE联邦学习任务")
async def submit_fate_job(
    name: str = Query(..., max_length=200, description="任务名称"),
    algorithm: str = Query(..., description="算法: homo_lr/hetero_lr/homo_nn/secureboost/psi/homo_statistic"),
    parties: str = Query(..., description="参与方配置JSON，如 [{\"role\":\"guest\",\"party_id\":9999}]"),
    dataset: str = Query(..., description="数据集名称"),
    epochs: int = Query(10, ge=1, le=1000, description="训练轮次"),
    model_params: Optional[str] = Query(None, description="额外模型参数JSON"),
    user: dict = Depends(get_current_user),
):
    """
    提交 FATE 联邦学习任务

    支持横向/纵向联邦学习、联邦统计、PSI 等算法
    FATE Flow 不可用时自动降级为本地模拟模式
    """
    party_list = json.loads(parties)
    extra_params = json.loads(model_params) if model_params else {}

    # 根据算法类型生成配置
    if algorithm == "homo_lr":
        job_config = fate_integration.generate_homo_lr_config(
            parties=party_list, dataset=dataset, epochs=epochs,
            learning_rate=extra_params.get("learning_rate", 0.1),
        )
    elif algorithm == "hetero_lr":
        guest_id = next((p["party_id"] for p in party_list if p.get("role") == "guest"), 9999)
        host_ids = [p["party_id"] for p in party_list if p.get("role") == "host"]
        job_config = fate_integration.generate_hetero_lr_config(
            guest_party_id=guest_id, host_party_ids=host_ids,
            guest_dataset=dataset, host_datasets=[dataset] * len(host_ids),
            epochs=epochs,
        )
    elif algorithm == "psi":
        job_config = fate_integration.generate_psi_config(
            parties=party_list, datasets=[dataset] * len(party_list),
        )
    else:
        # 通用配置
        job_config = {
            "dag_name": f"{algorithm}_{name}",
            "dsl_version": 2,
            "initiator": {"role": "guest", "party_id": party_list[0].get("party_id", 9999)},
            "role": {
                p.get("role", "host"): [p["party_id"]] for p in party_list
            },
            "component_parameters": {"common": {"train_data": {"name": dataset}}},
        }

    result = await fate_integration.submit_job(job_config)
    return ApiResponse(data=result)


@router.get("/fate/jobs", response_model=ApiResponse, summary="列出FATE任务")
async def list_fate_jobs(
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user),
):
    """列出所有 FATE 联邦学习任务（含远程和本地模拟）"""
    result = await fate_integration.list_jobs(limit=limit, offset=offset)
    return ApiResponse(data=result)


@router.get("/fate/jobs/{job_id}", response_model=ApiResponse, summary="查询FATE任务状态")
async def get_fate_job_status(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """查询 FATE 任务状态和结果"""
    status = await fate_integration.get_job_status(job_id)
    return ApiResponse(data=status)


@router.get("/fate/jobs/{job_id}/result", response_model=ApiResponse, summary="获取FATE任务结果")
async def get_fate_job_result(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """获取 FATE 任务结果（模型参数、评估指标等）"""
    result = await fate_integration.get_job_result(job_id)
    return ApiResponse(data=result)


@router.post("/fate/jobs/{job_id}/cancel", response_model=ApiResponse, summary="取消FATE任务")
async def cancel_fate_job(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """取消正在运行的 FATE 任务"""
    result = await fate_integration.get_job_manager().cancel(job_id)
    return ApiResponse(data=result)


@router.get("/fate/status", response_model=ApiResponse, summary="FATE服务状态")
async def get_fate_service_status(
    user: dict = Depends(get_current_user),
):
    """获取 FATE 服务连接状态、配置和性能指标"""
    info = fate_integration.get_fate_service_info()
    # 刷新健康状态
    healthy = await fate_integration.get_fate_client().check_health(force=True)
    info["health"]["is_healthy"] = healthy
    return ApiResponse(data=info)


@router.post("/fate/cleanup", response_model=ApiResponse, summary="清理过期任务")
async def cleanup_fate_jobs(
    max_age_hours: int = Query(24, ge=1, le=720, description="任务最大保留小时数"),
    user: dict = Depends(get_current_user),
):
    """清理过期的本地模拟任务"""
    removed = await fate_integration.get_job_manager().cleanup(max_age_hours)
    return ApiResponse(data={"removed_count": removed})


# ==================== 计算沙箱 ====================

@router.post("/sandbox/create", response_model=ApiResponse, summary="创建计算沙箱")
async def create_sandbox(
    task_id: str = Query(..., description="关联任务ID"),
    algorithm_code: str = Query(..., description="算法代码（Python脚本）"),
    data_refs: str = Query(..., description="数据引用列表（JSON数组）"),
    memory_limit: str = Query("2g", description="内存限制（如 2g, 512m）"),
    cpu_limit: str = Query("1.0", description="CPU限制"),
    timeout_seconds: int = Query(300, ge=10, le=3600, description="执行超时秒数"),
    user: dict = Depends(get_current_user),
):
    """
    创建计算沙箱

    安全策略：
    - 禁止网络访问（仅允许内部API调用）
    - 禁止文件系统写入（只读挂载数据）
    - 执行超时限制（默认300秒）
    - 内存限制（默认2GB）

    Docker 不可用时自动降级为进程级沙箱
    """
    refs = json.loads(data_refs)
    sandbox_id = await compute_sandbox.create_sandbox(
        task_id=task_id,
        algorithm_code=algorithm_code,
        data_refs=refs,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        timeout_seconds=timeout_seconds,
    )
    return ApiResponse(data={"sandbox_id": sandbox_id})


@router.post("/sandbox/{sandbox_id}/execute", response_model=ApiResponse, summary="执行沙箱任务")
async def execute_sandbox(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """
    执行沙箱任务

    自动执行：算法准入检查 → 沙箱执行 → 出口审核
    """
    result = await compute_sandbox.execute_sandbox(sandbox_id)
    return ApiResponse(data=result)


@router.delete("/sandbox/{sandbox_id}", response_model=ApiResponse, summary="销毁沙箱")
async def destroy_sandbox(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """销毁沙箱（运行中的沙箱会被强制停止）"""
    result = await compute_sandbox.destroy_sandbox(sandbox_id)
    return ApiResponse(data=result)


@router.get("/sandbox/{sandbox_id}/status", response_model=ApiResponse, summary="沙箱状态")
async def get_sandbox_status(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """获取沙箱状态"""
    result = await compute_sandbox.get_sandbox_status(sandbox_id)
    return ApiResponse(data=result)


# ==================== DAG 编排增强 ====================

@router.post("/dag/validate", response_model=ApiResponse, summary="验证DAG定义")
async def validate_dag(
    dag_definition: dict = Body(..., description="DAG定义（节点+边）"),
    user: dict = Depends(get_current_user),
):
    """
    验证 DAG 定义（不创建记录）

    检查：环检测、依赖完整性、类型兼容性
    返回验证结果和并行执行计划
    """
    result = await dag_engine.validate_dag(dag_definition)
    return ApiResponse(data=result)


@router.post("/dag/execute", response_model=ApiResponse, summary="执行DAG任务")
async def execute_dag(
    dag_id: str = Query(..., description="DAG ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    执行 DAG 任务

    支持并行执行无依赖节点，实时追踪每个节点状态
    """
    result = await dag_engine.execute_dag(
        db=db, dag_id=dag_id, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/dag/{task_id}/status", response_model=ApiResponse, summary="DAG执行状态")
async def get_dag_execution_status(
    task_id: str,
    execution_id: Optional[str] = Query(None, description="执行ID（可选）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询 DAG 执行状态（含每个节点状态和进度）"""
    result = await dag_engine.get_dag_execution_status(
        db=db, dag_id=task_id, execution_id=execution_id,
    )
    return ApiResponse(data=result)


@router.get("/dag/{task_id}/history", response_model=ApiResponse, summary="DAG执行历史")
async def get_dag_execution_history(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """获取 DAG 执行历史记录"""
    history = dag_engine.get_execution_history(task_id)
    return ApiResponse(data={"dag_id": task_id, "history": history})


# ==================== 隐私计算路由 ====================

@router.post("/route", response_model=ApiResponse, summary="隐私计算技术路由推荐")
async def route_privacy_task(
    task_description: str = Body(..., description="任务描述（自然语言）"),
    data_sensitivity: str = Body("high", description="数据敏感度: low/medium/high/critical"),
    participants: int = Body(2, ge=2, description="参与方数量"),
    scenario: Optional[str] = Body(None, description="业务场景（可选，自动推断）"),
    requirements: Optional[dict] = Body(None, description="额外需求"),
    user: dict = Depends(get_current_user),
):
    """
    隐私计算技术路由推荐

    路由矩阵：
    | 场景 | 推荐技术 | 备选 |
    |------|---------|------|
    | 联合预测 | FL(联邦学习) | MPC |
    | 安全结算 | MPC(安全多方计算) | TEE |
    | 调度优化 | TEE(可信执行环境) | FL |
    | 统计查询 | HE(同态加密) | DP |
    | 信用评估 | VFL(纵向联邦) | MPC |
    """
    result = await privacy_router.route_task(
        task_description=task_description,
        data_sensitivity=data_sensitivity,
        participants=participants,
        scenario=scenario,
        requirements=requirements,
    )
    return ApiResponse(data=result)


@router.get("/route/technologies", response_model=ApiResponse, summary="列出隐私计算技术")
async def list_technologies(
    user: dict = Depends(get_current_user),
):
    """列出所有隐私计算技术及可用状态"""
    result = await privacy_router.list_technologies()
    return ApiResponse(data=result)


@router.get("/route/scenarios", response_model=ApiResponse, summary="列出业务场景")
async def list_scenarios(
    user: dict = Depends(get_current_user),
):
    """列出所有支持的业务场景"""
    result = await privacy_router.list_scenarios()
    return ApiResponse(data=result)


@router.get("/route/status", response_model=ApiResponse, summary="引擎状态")
async def get_engine_status(
    user: dict = Depends(get_current_user),
):
    """检查各隐私计算引擎状态"""
    result = await privacy_router.check_engine_status()
    return ApiResponse(data=result)


@router.post("/route/execute", response_model=ApiResponse, summary="统一隐私计算执行")
async def execute_privacy_compute(
    mode: str = Query(..., description="计算模式: FL/MPC/TEE/HE/DP"),
    config: dict = Body(..., description="计算配置"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    通过统一接口执行隐私计算

    使用 PrivacyComputeInterface 的 run() 模板方法，
    自动处理 init → execute → cleanup 生命周期。
    """
    config["user_id"] = user.get("user_id", "")
    config["organization_id"] = user.get("organization_id", "00000000-0000-0000-0000-000000000000")
    result = await privacy_router.execute_privacy_compute(
        mode=mode,
        config=config,
        db=db,
    )
    return ApiResponse(data=result)
