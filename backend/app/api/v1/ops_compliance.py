"""
合规管理 API - /api/v1/ops/compliance
合规报告 + 检查清单 + 报告下载（Markdown / PDF）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.ops import ComplianceReportCreate, ComplianceReportResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import compliance_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/reports", response_model=ApiResponse[PaginatedResponse[ComplianceReportResponse]])
async def list_compliance_reports(
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    report_type: Optional[str] = Query(None, description="报告类型: data_security/gdpr/privacy"),
    status: Optional[str] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """合规报告列表"""
    result = await compliance_service.list_compliance_reports(
        db=db,
        params=pagination,
        organization_id=organization_id,
        report_type=report_type,
        status=status,
    )
    return ApiResponse(data=result)


@router.post("/reports/generate", response_model=ApiResponse[ComplianceReportResponse], status_code=201)
async def generate_compliance_report(
    request: ComplianceReportCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成合规报告"""
    result = await compliance_service.generate_compliance_report(
        db=db,
        request=request,
        generated_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/reports/{report_id}", response_model=ApiResponse[ComplianceReportResponse])
async def get_compliance_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """合规报告详情"""
    result = await compliance_service.get_compliance_report(
        db=db, report_id=report_id,
    )
    return ApiResponse(data=result)


@router.get("/checklist", response_model=ApiResponse)
async def get_compliance_checklist(
    report_type: Optional[str] = Query(None, description="报告类型"),
):
    """合规检查清单"""
    result = await compliance_service.get_compliance_checklist(
        report_type=report_type,
    )
    return ApiResponse(data=result)


@router.get("/reports/{report_id}/download/markdown", summary="下载 Markdown 报告")
async def download_report_markdown(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    下载合规报告 Markdown 格式

    返回 Markdown 文本文件。
    """
    try:
        content = await compliance_service.generate_report_markdown(
            db=db, report_id=report_id,
        )
        return PlainTextResponse(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="compliance_report_{report_id[:8]}.md"',
            },
        )
    except Exception as e:
        logger.error(f"Markdown report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@router.get("/reports/{report_id}/download/pdf", summary="下载 PDF 报告")
async def download_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    下载合规报告 PDF 格式

    使用 reportlab 生成 PDF，如果未安装则回退到 Markdown。
    """
    try:
        pdf_bytes = await compliance_service.generate_report_pdf(
            db=db, report_id=report_id,
        )

        # 检查是否为纯文本回退
        try:
            pdf_bytes.decode("utf-8")
            # 是文本回退，返回 Markdown
            return PlainTextResponse(
                content=pdf_bytes.decode("utf-8"),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="compliance_report_{report_id[:8]}.md"',
                },
            )
        except UnicodeDecodeError:
            # 正常 PDF
            import io
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="compliance_report_{report_id[:8]}.pdf"',
                },
            )
    except Exception as e:
        logger.error(f"PDF report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 报告生成失败: {str(e)}")
