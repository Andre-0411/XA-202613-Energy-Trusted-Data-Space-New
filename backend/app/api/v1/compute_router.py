"""
隐私计算路由 API - /api/v1/compute/router
根据业务场景自动选择技术路线
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.compute_router import (
    get_route_for_scenario,
    get_all_routes,
    suggest_task_type,
    merge_route_config,
    SCENARIO_ROUTE_MATRIX,
    TECH_CAPABILITIES,
)

router = APIRouter()


@router.get("/scenarios", response_model=ApiResponse)
async def list_scenarios():
    """列出所有支持的业务场景和技术路线"""
    routes = get_all_routes()
    return ApiResponse(data={
        "scenarios": routes,
        "total": len(routes),
    })


@router.get("/scenarios/{scenario}", response_model=ApiResponse)
async def get_scenario_route(scenario: str):
    """获取指定业务场景的技术路线"""
    try:
        route = get_route_for_scenario(scenario)
        return ApiResponse(data=route)
    except ValueError as e:
        return ApiResponse(code=2003, message=str(e), data=None)


@router.post("/suggest", response_model=ApiResponse)
async def suggest_route(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    智能推荐技术路线

    请求体:
    {
        "scenario": "power_forecast",  // 可选
        "data_size_mb": 100,           // 可选
        "num_participants": 3,         // 可选
        "requires_privacy": true       // 可选
    }
    """
    scenario = body.get("scenario")
    data_size_mb = body.get("data_size_mb", 0)
    num_participants = body.get("num_participants", 1)
    requires_privacy = body.get("requires_privacy", True)

    suggestion = suggest_task_type(
        scenario=scenario,
        data_size_mb=data_size_mb,
        num_participants=num_participants,
        requires_privacy=requires_privacy,
    )
    return ApiResponse(data=suggestion)


@router.post("/merge-config", response_model=ApiResponse)
async def merge_config(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    合并路由默认配置和用户自定义配置

    请求体:
    {
        "scenario": "power_forecast",
        "user_config": {"epochs": 20, "learning_rate": 0.001}
    }
    """
    scenario = body.get("scenario", "")
    user_config = body.get("user_config", {})

    if not scenario:
        return ApiResponse(code=2003, message="scenario 为必填项", data=None)

    try:
        merged = merge_route_config(scenario, user_config)
        return ApiResponse(data=merged)
    except ValueError as e:
        return ApiResponse(code=2003, message=str(e), data=None)


@router.get("/capabilities", response_model=ApiResponse)
async def get_capabilities():
    """获取所有技术路线的能力约束"""
    return ApiResponse(data=TECH_CAPABILITIES)


@router.get("/matrix", response_model=ApiResponse)
async def get_route_matrix():
    """获取完整路由矩阵"""
    return ApiResponse(data={
        "matrix": SCENARIO_ROUTE_MATRIX,
        "capabilities": TECH_CAPABILITIES,
    })
