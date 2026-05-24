"""
Excel 批量导入 API - /api/v1/ops/import
用户批量导入 + 数据资产批量导入
"""
import logging

from fastapi import APIRouter, Depends, File, UploadFile, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.import_data import ImportResult
from app.utils.deps import get_current_user
from app.services import excel_import_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/users",
    response_model=ApiResponse[ImportResult],
    summary="Excel 批量导入用户",
)
async def import_users_excel(
    file: UploadFile = File(..., description="Excel 文件（.xlsx）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    从 Excel 文件批量导入用户

    Excel 要求：
    - 第 1 行为表头
    - 必须包含列: username
    - 可选列: email, phone, role, organization_name, department_name
    - 最大 10000 行
    """
    file_content = await file.read()
    filename = file.filename or "unknown.xlsx"

    logger.info(
        f"用户批量导入请求: filename={filename}, size={len(file_content)}, "
        f"operator={user.get('user_id', '')}"
    )

    result = await excel_import_service.import_users_from_excel(
        db=db,
        file_content=file_content,
        filename=filename,
    )
    return ApiResponse(data=result)


@router.post(
    "/assets",
    response_model=ApiResponse[ImportResult],
    summary="Excel 批量导入数据资产",
)
async def import_assets_excel(
    file: UploadFile = File(..., description="Excel 文件（.xlsx）"),
    owner_id: str = Form(default="", description="资产拥有者 ID（可选）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    从 Excel 文件批量导入数据资产

    Excel 要求：
    - 第 1 行为表头
    - 必须包含列: name
    - 可选列: description, source_type, format, classification, security_level, tags
    - 最大 10000 行
    """
    file_content = await file.read()
    filename = file.filename or "unknown.xlsx"

    logger.info(
        f"资产批量导入请求: filename={filename}, size={len(file_content)}, "
        f"owner_id={owner_id}, operator={user.get('user_id', '')}"
    )

    effective_owner = owner_id if owner_id else user.get("user_id", "")

    result = await excel_import_service.import_assets_from_excel(
        db=db,
        file_content=file_content,
        filename=filename,
        owner_id=effective_owner,
    )
    return ApiResponse(data=result)
