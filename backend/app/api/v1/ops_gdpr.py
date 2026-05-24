"""
GDPR / 数安法合规 API - /api/v1/ops/gdpr
数据主体请求管理 + 数据导出 + 数据删除 + 统计
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.gdpr import (
    DataSubjectRequestCreate,
    DataSubjectRequestUpdate,
    DataSubjectRequestResponse,
    DataExportRequest,
    DataExportResponse,
    DataDeletionRequest,
    DataDeletionResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import gdpr_service

router = APIRouter()


@router.post(
    "/requests",
    response_model=ApiResponse[DataSubjectRequestResponse],
    status_code=201,
    summary="创建数据主体请求",
)
async def create_gdpr_request(
    request: DataSubjectRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建数据主体请求（access / erasure / portability / rectification / restrict_processing）

    GDPR 法规要求 30 天内响应。
    """
    result = await gdpr_service.create_request(db=db, request=request)
    return ApiResponse(data=result)


@router.get(
    "/requests",
    response_model=ApiResponse[PaginatedResponse[DataSubjectRequestResponse]],
    summary="数据主体请求列表",
)
async def list_gdpr_requests(
    request_type: Optional[str] = Query(None, description="请求类型: access/erasure/portability/rectification"),
    status: Optional[str] = Query(None, description="状态: pending/in_progress/completed/rejected"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询数据主体请求列表"""
    result = await gdpr_service.list_requests(
        db=db,
        params=pagination,
        request_type=request_type,
        status=status,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get(
    "/requests/{request_id}",
    response_model=ApiResponse[DataSubjectRequestResponse],
    summary="获取请求详情",
)
async def get_gdpr_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取数据主体请求详情"""
    result = await gdpr_service.get_request(db=db, request_id=request_id)
    return ApiResponse(data=result)


@router.put(
    "/requests/{request_id}",
    response_model=ApiResponse[DataSubjectRequestResponse],
    summary="更新请求状态",
)
async def update_gdpr_request(
    request_id: str,
    update: DataSubjectRequestUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    更新数据主体请求状态

    可更新字段: status, assigned_to, rejection_reason, response_data
    """
    result = await gdpr_service.update_request(
        db=db,
        request_id=request_id,
        update=update,
        operator_id=user.get("user_id"),
    )
    return ApiResponse(data=result)


@router.post(
    "/requests/{request_id}/process-access",
    response_model=ApiResponse[DataSubjectRequestResponse],
    summary="处理数据访问请求",
)
async def process_access_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    处理数据访问/可携带请求

    收集用户的所有数据（profile、审计日志、访问日志）并存入请求的 response_data。
    """
    result = await gdpr_service.process_access_request(db=db, request_id=request_id)
    return ApiResponse(data=result)


@router.post(
    "/requests/{request_id}/process-erasure",
    response_model=ApiResponse[DataSubjectRequestResponse],
    summary="处理数据删除请求",
)
async def process_erasure_request(
    request_id: str,
    retain_anonymized: bool = Query(
        default=True, description="是否保留匿名化数据（true=匿名化, false=硬删除）"
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    处理数据删除/被遗忘权请求

    默认匿名化处理（清除 user_id），也可选择硬删除。
    """
    result = await gdpr_service.process_erasure_request(
        db=db,
        request_id=request_id,
        retain_anonymized=retain_anonymized,
    )
    return ApiResponse(data=result)


@router.post(
    "/export",
    response_model=ApiResponse[DataExportResponse],
    summary="导出用户数据",
)
async def export_user_data(
    request: DataExportRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    导出用户数据（可携带权）

    支持 JSON / CSV 格式导出。
    """
    result = await gdpr_service.export_user_data(db=db, request=request)
    return ApiResponse(data=result)


@router.post(
    "/delete",
    response_model=ApiResponse[DataDeletionResponse],
    summary="删除用户数据",
)
async def delete_user_data(
    request: DataDeletionRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    删除用户数据

    必须确认 confirm=true。默认匿名化处理。
    """
    result = await gdpr_service.delete_user_data(db=db, request=request)
    return ApiResponse(data=result)


@router.get(
    "/statistics",
    response_model=ApiResponse,
    summary="GDPR 请求统计",
)
async def get_gdpr_statistics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取 GDPR 数据主体请求统计信息

    包括：按类型统计、按状态统计、逾期请求数量。
    """
    result = await gdpr_service.get_gdpr_statistics(db=db)
    return ApiResponse(data=result)
