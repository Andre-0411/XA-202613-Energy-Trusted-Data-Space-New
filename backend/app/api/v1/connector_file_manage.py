"""连接器文件库 API - /api/v1/connector-files"""
import logging
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.connector import (
    ConnectorFileResponse, FileSetCreate, FileSetResponse,
    ApiProxyCreate, ApiProxyResponse, ApiProxyTestResult,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import connector_file_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R046: 文件上传与管理 ====================

@router.post("/upload", response_model=ApiResponse[ConnectorFileResponse], status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    connector_id: str = Query(None, description="连接器ID"),
    file_set_id: str = Query(None, description="文件集ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """上传文件"""
    import os
    file_name = file.filename or "unknown"
    file_type = os.path.splitext(file_name)[1].lstrip(".") if "." in file_name else "unknown"
    content = await file.read()
    file_size = len(content)

    result = await connector_file_service.upload_file(
        db=db,
        connector_id=connector_id or "",
        file_name=file_name,
        file_path=f"uploads/{file_name}",
        file_type=file_type,
        uploaded_by=user["user_id"],
        file_size_bytes=file_size,
        file_set_id=file_set_id,
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[ConnectorFileResponse]])
async def list_files(
    pagination: PaginationParams = Depends(get_pagination_params),
    connector_id: str = Query(None, description="连接器ID"),
    file_type: str = Query(None, description="文件类型"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取文件列表"""
    result = await connector_file_service.list_files(
        db=db, params=pagination,
        connector_id=connector_id, file_type=file_type,
    )
    return ApiResponse(data=result)


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """下载文件"""
    result = await connector_file_service.download_file(
        db=db, file_id=file_id,
    )
    return result


# ==================== R047: 文件集管理 ====================

@router.post("/file-sets", response_model=ApiResponse[FileSetResponse], status_code=201)
async def create_file_set(
    request: FileSetCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建文件集"""
    result = await connector_file_service.create_file_set(
        db=db,
        name=request.name if hasattr(request, 'name') else "unnamed",
        organization_id=user["organization_id"],
        created_by=user["user_id"],
        description=request.description if hasattr(request, 'description') else None,
    )
    return ApiResponse(data=result)


@router.get("/file-sets", response_model=ApiResponse[PaginatedResponse[FileSetResponse]])
async def list_file_sets(
    pagination: PaginationParams = Depends(get_pagination_params),
    connector_id: str = Query(None, description="连接器ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取文件集列表"""
    result = await connector_file_service.list_file_sets(
        db=db, params=pagination,
        organization_id=user.get("organization_id"),
    )
    return ApiResponse(data=result)


@router.post("/file-sets/{file_set_id}/files", response_model=ApiResponse)
async def add_file_to_set(
    file_set_id: str,
    file_id: str = Query(..., description="文件ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """添加文件到文件集"""
    result = await connector_file_service.add_file_to_set(
        db=db, file_set_id=file_set_id, file_id=file_id,
    )
    return ApiResponse(data=result)


# ==================== R048: API代理管理 ====================

@router.post("/api-proxies", response_model=ApiResponse[ApiProxyResponse], status_code=201)
async def create_api_proxy(
    request: ApiProxyCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建API代理"""
    data = request.dict() if hasattr(request, 'dict') else request.model_dump()
    result = await connector_file_service.create_api_proxy(
        db=db,
        connector_id=data.get("connector_id", ""),
        name=data.get("name", ""),
        target_url=data.get("target_url", ""),
        created_by=user["user_id"],
        **{k: v for k, v in data.items() if k not in ("connector_id", "name", "target_url")},
    )
    return ApiResponse(data=result)


@router.get("/api-proxies", response_model=ApiResponse[PaginatedResponse[ApiProxyResponse]])
async def list_api_proxies(
    pagination: PaginationParams = Depends(get_pagination_params),
    connector_id: str = Query(None, description="连接器ID"),
    status: str = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取API代理列表"""
    result = await connector_file_service.list_api_proxies(
        db=db, organization_id=user["organization_id"],
        connector_id=connector_id, status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.post("/api-proxies/{proxy_id}/test", response_model=ApiResponse[ApiProxyTestResult])
async def test_api_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """测试API代理"""
    result = await connector_file_service.test_api_proxy(
        db=db, proxy_id=proxy_id,
    )
    return ApiResponse(data=result)


@router.post("/api-proxies/{proxy_id}/publish", response_model=ApiResponse)
async def publish_api_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """发布API代理"""
    result = await connector_file_service.publish_api_proxy(
        db=db, proxy_id=proxy_id,
    )
    return ApiResponse(data=result)
