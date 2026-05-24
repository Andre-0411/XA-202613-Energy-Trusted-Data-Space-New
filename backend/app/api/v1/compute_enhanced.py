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
from app.services import fate_integration, compute_sandbox, dag_engine, privacy_router, mpc_service, he_service

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


# ==================== 隐私计算演示 ====================

@router.post("/demo/full", response_model=ApiResponse, summary="运行完整隐私计算演示")
async def run_full_demo(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    运行完整的隐私计算演示

    演示内容：
    1. FATE 联邦学习（5方参与，1000条样本，Homo-LR）
    2. MPC 安全多方计算（3方求和1000次，<10秒）
    3. 同态加密（CKKS/BFV 密文运算）
    """
    from app.services.privacy_demo import run_full_privacy_demo

    result = await run_full_privacy_demo(
        db=db,
        user_id=user.get("user_id", ""),
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/demo/dataset", response_model=ApiResponse, summary="生成能源数据集")
async def generate_demo_dataset(
    num_samples: int = Query(1000, ge=100, le=10000, description="每方样本数"),
    num_parties: int = Query(5, ge=2, le=10, description="参与方数量"),
    user: dict = Depends(get_current_user),
):
    """
    生成能源领域联邦学习演示数据集

    用于赛题演示：5方参与，1000条样本
    """
    from app.services.privacy_demo import generate_energy_dataset

    dataset = generate_energy_dataset(
        num_samples=num_samples,
        num_parties=num_parties,
    )
    # 不返回完整数据，只返回元信息
    return ApiResponse(data={
        "dataset_name": dataset["dataset_name"],
        "num_parties": dataset["num_parties"],
        "num_samples_per_party": dataset["num_samples_per_party"],
        "num_features": dataset["num_features"],
        "feature_names": dataset["parties"]["party_0"]["feature_names"],
        "metadata": dataset["metadata"],
    })


@router.post("/demo/fate", response_model=ApiResponse, summary="FATE联邦学习演示")
async def run_fate_demo(
    num_parties: int = Query(5, ge=2, le=10, description="参与方数量"),
    num_samples: int = Query(1000, ge=100, le=10000, description="每方样本数"),
    epochs: int = Query(10, ge=1, le=100, description="训练轮次"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    FATE 联邦学习演示

    赛题要求：5方参与，1000条样本，训练时间<5分钟
    """
    config = fate_integration.generate_demo_homo_lr_config(
        num_parties=num_parties,
        sample_count=num_samples,
        epochs=epochs,
    )
    result = await fate_integration.submit_job(db, config)
    return ApiResponse(data={
        "demo": "fate_federated_learning",
        "config": config,
        "submission": result,
    })


@router.post("/demo/mpc", response_model=ApiResponse, summary="MPC安全计算演示")
async def run_mpc_demo(
    num_iterations: int = Query(1000, ge=100, le=10000, description="迭代次数"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    MPC 安全多方计算演示

    赛题要求：3方求和1000次 < 10秒
    """
    result = await mpc_service.run_mpc_demo_3party_sum(db, num_iterations=num_iterations)
    return ApiResponse(data=result)


@router.get("/demo/he/benchmark", response_model=ApiResponse, summary="同态加密性能基准")
async def run_he_benchmark(
    scheme: str = Query("ckks", description="HE方案: ckks/bfv"),
    poly_modulus_degree: int = Query(8192, description="多项式模数维度"),
    data_size: int = Query(1000, ge=100, le=10000, description="数据大小"),
    user: dict = Depends(get_current_user),
):
    """
    同态加密性能基准测试

    测试 CKKS/BFV 方案的加密、运算、解密性能
    """
    result = await he_service.run_he_benchmark(
        scheme=scheme,
        poly_modulus_degree=poly_modulus_degree,
        data_size=data_size,
    )
    return ApiResponse(data=result)


@router.post("/demo/he/operate", response_model=ApiResponse, summary="同态加密运算演示")
async def run_he_demo(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    同态加密运算演示

    演示 CKKS/BFV 方案的密文加法和乘法
    """
    result = await he_service.run_he_operation_demo(
        db=db,
        user_id=user.get("user_id", ""),
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/demo/tee/benchmark", response_model=ApiResponse, summary="TEE性能基准")
async def run_tee_benchmark(
    user: dict = Depends(get_current_user),
):
    """
    TEE 性能基准测试

    测试 SM4-GCM、SM3、AES-256-GCM、SGX 飞地模拟性能
    """
    from app.services.tee_service import run_tee_performance_benchmark

    result = await run_tee_performance_benchmark()
    return ApiResponse(data=result)


@router.post("/demo/tee/sgx", response_model=ApiResponse, summary="SGX飞地Python执行演示")
async def run_sgx_demo(
    python_code: str = Body(..., description="Python代码"),
    input_data: dict = Body(..., description="输入数据"),
    memory_size_mb: int = Body(512, description="飞地内存大小(MB)"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    SGX 飞地 Python 代码执行演示

    模拟 Intel SGX + Gramine 环境下的 Python 应用安全执行
    """
    from app.services.tee_service import execute_python_in_sgx_enclave

    result = await execute_python_in_sgx_enclave(
        db=db,
        user_id=user.get("user_id", ""),
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
        python_code=python_code,
        input_data=input_data,
        memory_size_mb=memory_size_mb,
    )
    return ApiResponse(data=result)
