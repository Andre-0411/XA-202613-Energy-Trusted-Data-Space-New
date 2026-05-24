"""
性能基准测试服务
各隐私计算算法性能对比 / 执行时间趋势 / 资源使用率
"""
import uuid
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

# 支持的算法及默认性能参数
ALGORITHM_DEFAULTS = {
    "MPC": {
        "name": "MPC 安全多方计算",
        "base_time_ms": 12500,
        "variance": 0.3,
        "cpu_base": 78,
        "mem_base_mb": 512,
        "throughput_base": 320,
    },
    "FL": {
        "name": "联邦学习",
        "base_time_ms": 45300,
        "variance": 0.4,
        "cpu_base": 92,
        "mem_base_mb": 1024,
        "throughput_base": 85,
    },
    "TEE": {
        "name": "TEE 可信执行",
        "base_time_ms": 3200,
        "variance": 0.25,
        "cpu_base": 55,
        "mem_base_mb": 256,
        "throughput_base": 1200,
    },
    "HE": {
        "name": "同态加密",
        "base_time_ms": 28700,
        "variance": 0.35,
        "cpu_base": 88,
        "mem_base_mb": 768,
        "throughput_base": 150,
    },
    "DP": {
        "name": "差分隐私",
        "base_time_ms": 1500,
        "variance": 0.2,
        "cpu_base": 35,
        "mem_base_mb": 128,
        "throughput_base": 2800,
    },
    "Sandbox": {
        "name": "沙箱计算",
        "base_time_ms": 8900,
        "variance": 0.3,
        "cpu_base": 65,
        "mem_base_mb": 384,
        "throughput_base": 520,
    },
}

# 基准存储
_benchmarks: dict[str, dict] = {}

# 趋势数据存储（最近100条）
_trend_data: list[dict] = []


# ==================== 基准接口 ====================

async def run_benchmark(
    algorithms: list[str],
    iterations: int = 10,
    data_size: int = 1000,
    participants: int = 2,
    config_override: Optional[dict] = None,
) -> dict:
    """
    运行基准测试

    对指定算法进行多轮模拟测试，收集性能指标

    Args:
        algorithms: 要测试的算法列表
        iterations: 测试迭代次数
        data_size: 测试数据规模
        participants: 参与方数量
        config_override: 覆盖配置

    Returns:
        基准测试结果
    """
    benchmark_id = str(uuid.uuid4())

    # 校验算法
    invalid = [a for a in algorithms if a not in ALGORITHM_DEFAULTS]
    if invalid:
        return {
            "benchmark_id": benchmark_id,
            "status": "failed",
            "error": f"不支持的算法: {invalid}，允许值: {list(ALGORITHM_DEFAULTS.keys())}",
        }

    started_at = datetime.now(timezone.utc).isoformat()

    # 执行模拟基准测试
    results = []
    for algo in algorithms:
        result = _simulate_algorithm_benchmark(
            algo, iterations, data_size, participants, config_override
        )
        results.append(result)

    completed_at = datetime.now(timezone.utc).isoformat()

    benchmark = {
        "benchmark_id": benchmark_id,
        "status": "completed",
        "algorithms": algorithms,
        "iterations": iterations,
        "data_size": data_size,
        "participants": participants,
        "results": results,
        "started_at": started_at,
        "completed_at": completed_at,
        "total_time_ms": sum(r["avg_time_ms"] for r in results),
    }

    _benchmarks[benchmark_id] = benchmark

    # 记录趋势数据
    for result in results:
        _trend_data.append({
            "timestamp": completed_at,
            "algorithm": result["algorithm"],
            "avg_time_ms": result["avg_time_ms"],
            "throughput": result["throughput"],
            "cpu_usage_percent": result["cpu_usage_percent"],
            "memory_usage_mb": result["memory_usage_mb"],
        })
        # 保留最近100条
        if len(_trend_data) > 100:
            _trend_data.pop(0)

    logger.info(
        f"Benchmark completed: {benchmark_id}, algorithms={algorithms}, "
        f"iterations={iterations}, data_size={data_size}"
    )
    return benchmark


async def get_benchmark(benchmark_id: str) -> dict:
    """获取基准测试详情"""
    benchmark = _benchmarks.get(benchmark_id)
    if not benchmark:
        return {"error": "基准测试未找到", "benchmark_id": benchmark_id}
    return benchmark


async def list_benchmarks(
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """查询基准测试列表"""
    all_benchmarks = sorted(
        _benchmarks.values(),
        key=lambda b: b.get("started_at", ""),
        reverse=True,
    )

    total = len(all_benchmarks)
    items = all_benchmarks[offset:offset + limit]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_benchmark_summary() -> dict:
    """获取基准测试摘要"""
    all_benchmarks = list(_benchmarks.values())

    if not all_benchmarks:
        # 返回默认数据
        default_results = _get_default_benchmark_results()
        return {
            "total_benchmarks": 0,
            "algorithms_tested": list(ALGORITHM_DEFAULTS.keys()),
            "latest_benchmark_id": None,
            "latest_results": default_results,
        }

    # 获取最新基准
    latest = max(all_benchmarks, key=lambda b: b.get("started_at", ""))
    algorithms_tested = list(set(
        r["algorithm"] for b in all_benchmarks for r in b.get("results", [])
    ))

    return {
        "total_benchmarks": len(all_benchmarks),
        "algorithms_tested": algorithms_tested,
        "latest_benchmark_id": latest.get("benchmark_id"),
        "latest_results": latest.get("results", []),
    }


async def get_trend_data(
    algorithm: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """获取趋势数据"""
    data = _trend_data
    if algorithm:
        data = [d for d in data if d.get("algorithm") == algorithm]
    return data[-limit:]


async def export_benchmark_report(
    benchmark_ids: list[str],
    format_type: str = "json",
) -> dict:
    """导出基准测试报告"""
    report_benchmarks = []
    for bid in benchmark_ids:
        b = _benchmarks.get(bid)
        if b:
            report_benchmarks.append(b)

    if not report_benchmarks:
        return {"error": "未找到指定的基准测试"}

    return {
        "format": format_type,
        "benchmark_count": len(report_benchmarks),
        "benchmarks": report_benchmarks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _get_default_benchmark_results() -> list[dict]:
    """获取默认基准结果（用于页面初始展示）"""
    results = []
    for algo, config in ALGORITHM_DEFAULTS.items():
        base_time = config["base_time_ms"]
        variance = config["variance"]

        results.append({
            "algorithm": algo,
            "algorithm_name": config["name"],
            "avg_time_ms": base_time,
            "min_time_ms": round(base_time * (1 - variance), 1),
            "max_time_ms": round(base_time * (1 + variance), 1),
            "p50_time_ms": round(base_time * 0.95, 1),
            "p95_time_ms": round(base_time * (1 + variance * 0.7), 1),
            "p99_time_ms": round(base_time * (1 + variance), 1),
            "throughput": config["throughput_base"],
            "cpu_usage_percent": config["cpu_base"],
            "memory_usage_mb": config["mem_base_mb"],
            "task_count": random.randint(50, 300),
            "success_rate": round(random.uniform(0.95, 0.999), 3),
            "iterations": 0,
        })
    return results


def _simulate_algorithm_benchmark(
    algorithm: str,
    iterations: int,
    data_size: int,
    participants: int,
    config_override: Optional[dict] = None,
) -> dict:
    """
    模拟单算法基准测试

    基于默认参数 + 随机方差生成性能指标
    """
    config = ALGORITHM_DEFAULTS.get(algorithm, ALGORITHM_DEFAULTS["MPC"])
    overrides = (config_override or {}).get(algorithm, {})

    base_time = overrides.get("base_time_ms", config["base_time_ms"])
    variance = config["variance"]

    # 数据规模和参与方数量影响
    scale_factor = max(1.0, data_size / 1000) * max(1.0, participants / 2)
    adjusted_base = base_time * scale_factor

    # 模拟多次迭代
    times = []
    for _ in range(max(iterations, 1)):
        t = adjusted_base * random.uniform(1 - variance, 1 + variance)
        times.append(max(1.0, t))

    times.sort()
    n = len(times)

    avg_time = sum(times) / n
    min_time = times[0]
    max_time = times[-1]
    p50 = times[n // 2]
    p95 = times[int(n * 0.95)] if n > 1 else max_time
    p99 = times[int(n * 0.99)] if n > 1 else max_time

    cpu_usage = min(99.0, config["cpu_base"] * random.uniform(0.85, 1.15))
    mem_mb = config["mem_base_mb"] * random.uniform(0.8, 1.2) * scale_factor
    throughput = max(1.0, config["throughput_base"] / scale_factor * random.uniform(0.8, 1.2))

    return {
        "algorithm": algorithm,
        "algorithm_name": config["name"],
        "avg_time_ms": round(avg_time, 1),
        "min_time_ms": round(min_time, 1),
        "max_time_ms": round(max_time, 1),
        "p50_time_ms": round(p50, 1),
        "p95_time_ms": round(p95, 1),
        "p99_time_ms": round(p99, 1),
        "throughput": round(throughput, 1),
        "cpu_usage_percent": round(cpu_usage, 1),
        "memory_usage_mb": round(mem_mb, 1),
        "task_count": iterations,
        "success_rate": round(random.uniform(0.95, 0.999), 3),
        "iterations": iterations,
    }
