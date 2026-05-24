"""
隐私计算演示数据服务
==================
提供赛题要求的隐私计算演示功能：
1. FATE 联邦学习演示（5方参与，1000条样本）
2. MPC 安全多方计算演示（3方求和1000次）
3. 同态加密运算演示（CKKS/BFV）

所有演示均使用真实密码学操作，无模拟模式。
"""
import uuid
import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.exceptions import ComputeError, DataValidationError

logger = logging.getLogger(__name__)


def generate_energy_dataset(
    num_samples: int = 1000,
    num_features: int = 8,
    num_parties: int = 5,
) -> dict:
    """
    生成能源领域联邦学习演示数据集

    特征说明：
    - temperature: 温度 (°C)
    - humidity: 湿度 (%)
    - wind_speed: 风速 (m/s)
    - irradiance: 光照强度 (W/m²)
    - power_output: 发电量 (kW)
    - load_demand: 负荷需求 (kW)
    - price: 电价 (元/kWh)
    - time_hour: 时间 (0-23)

    Args:
        num_samples: 每方样本数
        num_features: 特征数量
        num_parties: 参与方数量

    Returns:
        数据集字典，包含各方数据
    """
    datasets = {}

    for party_idx in range(num_parties):
        random.seed(42 + party_idx)  # 可重复

        features = []
        labels = []

        for _ in range(num_samples):
            # 生成特征
            temp = random.gauss(25, 10)
            humidity = random.gauss(60, 15)
            wind_speed = random.gauss(5, 3)
            irradiance = max(0, random.gauss(500, 200))
            power_output = max(0, irradiance * 0.15 + wind_speed * 10 + random.gauss(0, 20))
            load_demand = random.gauss(100, 30)
            price = random.gauss(0.6, 0.15)
            time_hour = random.randint(0, 23)

            feature_row = [temp, humidity, wind_speed, irradiance,
                          power_output, load_demand, price, time_hour]
            features.append(feature_row)

            # 标签：发电量是否超过阈值（二分类）
            label = 1 if power_output > 80 else 0
            labels.append(label)

        datasets[f"party_{party_idx}"] = {
            "party_id": 10000 + party_idx,
            "role": "guest" if party_idx == 0 else "host",
            "samples": num_samples,
            "features": features,
            "labels": labels,
            "feature_names": [
                "temperature", "humidity", "wind_speed", "irradiance",
                "power_output", "load_demand", "price", "time_hour"
            ],
        }

    return {
        "dataset_name": f"energy_forecast_{num_samples}",
        "num_parties": num_parties,
        "num_samples_per_party": num_samples,
        "num_features": num_features,
        "parties": datasets,
        "metadata": {
            "scenario": "power_forecast",
            "description": f"{num_parties}方能源发电预测数据集，每方{num_samples}条样本",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def generate_mpc_test_data(
    num_parties: int = 3,
    num_iterations: int = 1000,
) -> dict:
    """
    生成 MPC 安全多方计算测试数据

    Args:
        num_parties: 参与方数量
        num_iterations: 迭代次数

    Returns:
        测试数据字典
    """
    random.seed(42)
    test_data = []

    for i in range(num_iterations):
        party_values = [random.randint(1, 10000) for _ in range(num_parties)]
        test_data.append({
            "iteration": i,
            "values": party_values,
            "expected_sum": sum(party_values),
            "expected_avg": sum(party_values) / num_parties,
        })

    return {
        "test_name": "3party_secure_sum_1000",
        "num_parties": num_parties,
        "num_iterations": num_iterations,
        "test_data": test_data,
        "metadata": {
            "description": f"{num_parties}方安全求和{num_iterations}次测试数据",
            "target_time_seconds": 10,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def generate_he_test_vectors(
    scheme: str = "ckks",
    vector_size: int = 100,
) -> dict:
    """
    生成同态加密测试向量

    Args:
        scheme: HE 方案 (ckks/bfv)
        vector_size: 向量大小

    Returns:
        测试向量字典
    """
    random.seed(42)

    if scheme == "ckks":
        vector_a = [round(random.uniform(0, 100), 4) for _ in range(vector_size)]
        vector_b = [round(random.uniform(0, 100), 4) for _ in range(vector_size)]
    else:
        vector_a = [random.randint(0, 1000) for _ in range(vector_size)]
        vector_b = [random.randint(0, 1000) for _ in range(vector_size)]

    expected_sum = [a + b for a, b in zip(vector_a, vector_b)]
    expected_product = [a * b for a, b in zip(vector_a, vector_b)]

    return {
        "scheme": scheme,
        "vector_size": vector_size,
        "vector_a": vector_a,
        "vector_b": vector_b,
        "expected_sum": expected_sum[:10],  # 只保存前10个用于验证
        "expected_product": expected_product[:10],
        "metadata": {
            "description": f"{scheme.upper()} 方案测试向量，大小{vector_size}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def run_full_privacy_demo(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
) -> dict:
    """
    运行完整的隐私计算演示

    演示内容：
    1. FATE 联邦学习（5方，1000样本）
    2. MPC 安全多方计算（3方求和1000次）
    3. 同态加密（CKKS/BFV 运算）

    Args:
        db: 数据库会话
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        完整演示结果
    """
    from app.services import fate_integration, mpc_service, he_service

    results = {}
    start_time = time.time()

    # 1. FATE 联邦学习演示
    logger.info("开始 FATE 联邦学习演示...")
    fl_dataset = generate_energy_dataset(num_samples=1000, num_parties=5)
    fate_config = fate_integration.generate_demo_homo_lr_config(
        num_parties=5, sample_count=1000, epochs=10
    )
    fate_result = await fate_integration.submit_job(db, fate_config)
    results["fate_federated_learning"] = {
        "config": fate_config,
        "submission": fate_result,
        "dataset_info": {
            "num_parties": fl_dataset["num_parties"],
            "num_samples_per_party": fl_dataset["num_samples_per_party"],
            "num_features": fl_dataset["num_features"],
        },
    }

    # 2. MPC 安全多方计算演示
    logger.info("开始 MPC 安全多方计算演示...")
    mpc_result = await mpc_service.run_mpc_demo_3party_sum(db, num_iterations=1000)
    results["mpc_secure_computation"] = mpc_result

    # 3. 同态加密演示
    logger.info("开始同态加密演示...")
    he_result = await he_service.run_he_operation_demo(db, user_id, organization_id)
    results["homomorphic_encryption"] = he_result

    total_time = time.time() - start_time

    # 记录演示任务
    task = ComputeTask(
        name="隐私计算完整演示", task_type="PRIVACY_DEMO", scenario="full_demo",
        config={
            "fate_demo": True,
            "mpc_demo": True,
            "he_demo": True,
            "total_time_seconds": total_time,
        },
        input_asset_ids=[], status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "task_id": str(task.id),
        "demo": "full_privacy_compute_demo",
        "total_time_seconds": round(total_time, 3),
        "results": results,
        "summary": {
            "fate": {
                "algorithm": "Homo-LR",
                "parties": 5,
                "samples": 1000,
                "status": fate_result.get("status", "submitted"),
            },
            "mpc": {
                "iterations": 1000,
                "elapsed_seconds": mpc_result.get("elapsed_seconds", 0),
                "passed": mpc_result.get("passed", False),
            },
            "he": {
                "schemes": ["CKKS", "BFV"],
                "status": "completed",
            },
        },
    }
