"""
性能基准测试 API - /api/v1/compute/benchmarks
运行基准测试 / 查询结果 / 获取摘要 / 导出报告
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.common import ApiResponse
from app.schemas.benchmark import (
    BenchmarkRequest, BenchmarkResponse, BenchmarkSummary,
    BenchmarkExportRequest,
)
from app.utils.deps import get_current_user
from app.services import benchmark_service

router = APIRouter()


@router.post("", response_model=ApiResponse[BenchmarkResponse], status_code=201)
async def run_benchmark(
    request: BenchmarkRequest,
    user: dict = Depends(get_current_user),
):
    """
    运行性能基准测试

    对指定算法进行多轮模拟测试，收集性能指标
    """
    result = await benchmark_service.run_benchmark(
        algorithms=request.algorithms,
        iterations=request.iterations,
        data_size=request.data_size,
        participants=request.participants,
        config_override=request.config_override,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse)
async def list_benchmarks(
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user),
):
    """查询基准测试列表"""
    result = await benchmark_service.list_benchmarks(limit=limit, offset=offset)
    return ApiResponse(data=result)


@router.get("/summary", response_model=ApiResponse[BenchmarkSummary])
async def get_benchmark_summary(
    user: dict = Depends(get_current_user),
):
    """获取基准测试摘要（包含最新结果和统计）"""
    result = await benchmark_service.get_benchmark_summary()
    return ApiResponse(data=result)


@router.get("/trends", response_model=ApiResponse)
async def get_trend_data(
    algorithm: Optional[str] = Query(None, description="算法过滤: MPC/FL/TEE/HE/DP/Sandbox"),
    limit: int = Query(50, ge=1, le=200, description="数据点数量"),
    user: dict = Depends(get_current_user),
):
    """获取性能趋势数据（用于折线图展示）"""
    result = await benchmark_service.get_trend_data(algorithm=algorithm, limit=limit)
    return ApiResponse(data=result)


@router.get("/{benchmark_id}", response_model=ApiResponse[BenchmarkResponse])
async def get_benchmark(
    benchmark_id: str,
    user: dict = Depends(get_current_user),
):
    """获取基准测试详情"""
    result = await benchmark_service.get_benchmark(benchmark_id)
    if "error" in result:
        return ApiResponse(code=404, message=result["error"], data=None)
    return ApiResponse(data=result)


@router.post("/export", response_model=ApiResponse)
async def export_benchmark_report(
    request: BenchmarkExportRequest,
    user: dict = Depends(get_current_user),
):
    """导出基准测试报告"""
    result = await benchmark_service.export_benchmark_report(
        benchmark_ids=request.benchmark_ids,
        format_type=request.format_type,
    )
    if "error" in result:
        return ApiResponse(code=400, message=result["error"], data=None)
    return ApiResponse(data=result)