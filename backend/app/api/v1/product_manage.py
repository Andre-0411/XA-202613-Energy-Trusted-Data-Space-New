"""数据产品管理 API - /api/v1/product-projects & /api/v1/data-products"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.product import (
    ProductProjectCreate, ProductProjectResponse,
    ProjectMemberAdd, DataSourceConfig,
    DataProductCreate, DataProductResponse, DataProductUpdate,
    ComputeEngineConfig, ProductAcceptance,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import product_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R020: 项目管理 ====================

@router.post("/projects", response_model=ApiResponse[ProductProjectResponse], status_code=201)
async def create_project(
    request: ProductProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建项目"""
    result = await product_service.create_project(
        db=db,
        owner_id=user["user_id"],
        organization_id=user["organization_id"],
        data=request.dict(),
    )
    return ApiResponse(data=result)


@router.get("/projects", response_model=ApiResponse[PaginatedResponse[ProductProjectResponse]])
async def list_projects(
    pagination: PaginationParams = Depends(get_pagination_params),
    project_type: str = Query(None, description="项目类型"),
    status: str = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取项目列表"""
    result = await product_service.list_projects(
        db=db, organization_id=user.get("organization_id"),
        project_type=project_type, status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/projects/{project_id}", response_model=ApiResponse[ProductProjectResponse])
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取项目详情"""
    result = await product_service.get_project(db=db, project_id=project_id)
    return ApiResponse(data=result)


@router.post("/projects/{project_id}/members", response_model=ApiResponse)
async def add_project_member(
    project_id: str,
    request: ProjectMemberAdd,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """添加项目成员"""
    result = await product_service.add_member(
        db=db, project_id=project_id,
        user_id=request.user_id, role=request.role,
    )
    return ApiResponse(data=result)


@router.post("/projects/{project_id}/data-sources", response_model=ApiResponse)
async def configure_project_data_sources(
    project_id: str,
    request: DataSourceConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置项目数据源"""
    result = await product_service.configure_data_sources(
        db=db, project_id=project_id, data_sources=request.data_sources,
    )
    return ApiResponse(data=result)


# ==================== R021: 数据产品 ====================

@router.post("/", response_model=ApiResponse[DataProductResponse], status_code=201)
async def create_product(
    request: DataProductCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据产品"""
    result = await product_service.create_product(
        db=db,
        owner_id=user["user_id"],
        organization_id=user["organization_id"],
        data=request.dict(),
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[DataProductResponse]])
async def list_products(
    pagination: PaginationParams = Depends(get_pagination_params),
    product_type: str = Query(None, description="产品类型"),
    status: str = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取产品列表"""
    result = await product_service.list_products(
        db=db, organization_id=user.get("organization_id"),
        product_type=product_type, status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/{product_id}", response_model=ApiResponse[DataProductResponse])
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取产品详情"""
    result = await product_service.get_product(db=db, product_id=product_id)
    return ApiResponse(data=result)


@router.put("/{product_id}", response_model=ApiResponse[DataProductResponse])
async def update_product(
    product_id: str,
    request: DataProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新产品"""
    result = await product_service.update_product(
        db=db, product_id=product_id, data=request.dict(exclude_unset=True),
    )
    return ApiResponse(data=result)


# ==================== R022: 计算引擎配置 ====================

@router.post("/{product_id}/compute-engine", response_model=ApiResponse)
async def configure_compute_engine(
    product_id: str,
    request: ComputeEngineConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置计算引擎"""
    result = await product_service.configure_compute_engine(
        db=db, product_id=product_id, engine_config=request.dict(),
    )
    return ApiResponse(data=result)


# ==================== R027: 产品验收 ====================

@router.post("/{product_id}/accept", response_model=ApiResponse)
async def accept_product(
    product_id: str,
    request: ProductAcceptance,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """产品验收"""
    result = await product_service.accept_product(
        db=db, product_id=product_id,
        acceptor_id=user["user_id"],
        test_result=request.test_result,
        status=request.status,
        comment=request.comment,
    )
    return ApiResponse(data=result)
