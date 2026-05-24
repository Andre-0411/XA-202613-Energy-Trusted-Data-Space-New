"""
计算结果 API - /api/v1/compute/results
结果加密存储 + 哈希上链 + 解密接收
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.compute_result_service import (
    store_encrypted_result,
    retrieve_and_decrypt_result,
    verify_result_integrity,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/store", response_model=ApiResponse)
async def store_result(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    加密存储计算结果并上链存证

    请求体:
    {
        "task_id": "xxx",
        "result_data": "base64编码的结果数据",
        "result_format": "json",
        "metadata": {}
    }
    """
    import base64

    task_id = body.get("task_id", "")
    result_data_b64 = body.get("result_data", "")
    result_format = body.get("result_format", "json")
    metadata = body.get("metadata")

    if not task_id:
        return ApiResponse(code=2003, message="task_id 为必填项", data=None)
    if not result_data_b64:
        return ApiResponse(code=2003, message="result_data 为必填项", data=None)

    try:
        result_data = base64.b64decode(result_data_b64)
    except Exception:
        # 尝试直接使用字符串
        result_data = result_data_b64.encode("utf-8")

    try:
        result = await store_encrypted_result(
            db=db,
            task_id=task_id,
            result_data=result_data,
            result_format=result_format,
            metadata=metadata,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Result storage failed: {e}")
        return ApiResponse(code=4020, message=f"结果存储失败: {e}", data=None)


@router.get("/{task_id}/results/{result_id}/decrypt")
async def decrypt_result(
    task_id: str,
    result_id: str,
    encryption_key_id: str = Query(..., description="加密密钥 ID"),
    user: dict = Depends(get_current_user),
):
    """解密并返回计算结果"""
    try:
        decrypted = await retrieve_and_decrypt_result(
            task_id=task_id,
            result_id=result_id,
            encryption_key_id=encryption_key_id,
        )
        return Response(
            content=decrypted,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="result_{result_id}.bin"'
            },
        )
    except Exception as e:
        logger.error(f"Result decryption failed: {e}")
        return ApiResponse(code=4020, message=f"结果解密失败: {e}", data=None)


@router.get("/{task_id}/results/{result_id}/verify", response_model=ApiResponse)
async def verify_result(
    task_id: str,
    result_id: str,
    expected_hash: str = Query(..., description="期望的 SM3 哈希"),
    user: dict = Depends(get_current_user),
):
    """验证计算结果完整性"""
    result = await verify_result_integrity(
        task_id=task_id,
        result_id=result_id,
        expected_hash=expected_hash,
    )
    return ApiResponse(data=result)
