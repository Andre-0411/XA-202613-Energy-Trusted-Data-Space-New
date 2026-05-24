"""
AI Agent 管理 API - /api/v1/agents
知识库管理、模型配置、Agent 参数调节
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.agent_manage import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    DocumentUpload,
    ModelConfig,
    AgentConfigUpdate,
)
from app.utils.deps import get_current_user
from app.services import agent_manage_service

router = APIRouter()


# ==================== 统计数据 ====================

@router.get("/stats", response_model=ApiResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Agent 统计数据"""
    result = await agent_manage_service.get_agent_stats(db)
    return ApiResponse(data=result)


# ==================== Agent 配置 ====================

@router.get("/configs", response_model=ApiResponse)
async def list_agent_configs(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取所有 Agent 配置"""
    result = await agent_manage_service.list_agent_configs(db)
    return ApiResponse(data=result)


@router.get("/configs/{agent_type}", response_model=ApiResponse)
async def get_agent_config(
    agent_type: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取指定 Agent 配置"""
    result = await agent_manage_service.get_agent_config(db, agent_type)
    return ApiResponse(data=result)


@router.put("/configs/{agent_type}", response_model=ApiResponse)
async def update_agent_config(
    agent_type: str,
    body: AgentConfigUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新 Agent 配置"""
    result = await agent_manage_service.update_agent_config(
        db=db,
        agent_type=agent_type,
        data=body.model_dump(exclude_unset=True),
    )
    return ApiResponse(data=result)


# ==================== 模型配置 ====================

@router.get("/model-config", response_model=ApiResponse)
async def get_model_config(
    user: dict = Depends(get_current_user),
):
    """获取模型配置"""
    result = await agent_manage_service.get_model_config()
    return ApiResponse(data=result)


@router.put("/model-config", response_model=ApiResponse)
async def update_model_config(
    body: ModelConfig = Body(...),
    user: dict = Depends(get_current_user),
):
    """更新模型配置"""
    result = await agent_manage_service.update_model_config(
        data=body.model_dump(exclude_unset=True),
    )
    return ApiResponse(data=result)


# ==================== 知识库管理 ====================

@router.get("/knowledge-bases", response_model=ApiResponse)
async def list_knowledge_bases(
    category: Optional[str] = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取知识库列表"""
    result = await agent_manage_service.list_knowledge_bases(
        db=db,
        category=category,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=result)


@router.post("/knowledge-bases", response_model=ApiResponse)
async def create_knowledge_base(
    body: KnowledgeBaseCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建知识库"""
    result = await agent_manage_service.create_knowledge_base(
        db=db,
        data=body.model_dump(),
    )
    return ApiResponse(data=result)


@router.get("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取知识库详情"""
    result = await agent_manage_service.get_knowledge_base(db, kb_id)
    return ApiResponse(data=result)


@router.put("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def update_knowledge_base(
    kb_id: str,
    body: KnowledgeBaseUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新知识库"""
    result = await agent_manage_service.update_knowledge_base(
        db=db,
        kb_id=kb_id,
        data=body.model_dump(exclude_unset=True),
    )
    return ApiResponse(data=result)


@router.delete("/knowledge-bases/{kb_id}", response_model=ApiResponse)
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除知识库"""
    await agent_manage_service.delete_knowledge_base(db, kb_id)
    return ApiResponse(message="知识库已删除")


# ==================== 文档管理 ====================

@router.get("/knowledge-bases/{kb_id}/documents", response_model=ApiResponse)
async def list_documents(
    kb_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取知识库文档列表"""
    result = await agent_manage_service.list_documents(
        db=db,
        kb_id=kb_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=result)


@router.post("/knowledge-bases/{kb_id}/documents", response_model=ApiResponse)
async def add_document(
    kb_id: str,
    body: DocumentUpload = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """添加文档到知识库"""
    result = await agent_manage_service.add_document(
        db=db,
        kb_id=kb_id,
        data=body.model_dump(),
    )
    return ApiResponse(data=result)


@router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}", response_model=ApiResponse)
async def delete_document(
    kb_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除文档"""
    await agent_manage_service.delete_document(db, kb_id, doc_id)
    return ApiResponse(message="文档已删除")


# ==================== 工具注册表 ====================


@router.get("/tools", response_model=ApiResponse)
async def get_tool_registry(
    user: dict = Depends(get_current_user),
):
    """获取 Agent 工具注册表（所有可用工具）"""
    from app.services.tool_registry import get_all_tools, get_registry_stats

    tools = get_all_tools()
    stats = get_registry_stats()

    tool_list = []
    for name, entry in tools.items():
        tool_list.append({
            "name": name,
            "module": entry["module"],
            "method": entry["method"],
            "path": entry["path"],
            "description": entry["description"],
            "auto_generated": entry.get("auto_generated", False),
        })

    return ApiResponse(data={
        "tools": tool_list,
        "stats": stats,
    })


@router.get("/tools/{agent_type}", response_model=ApiResponse)
async def get_agent_tools(
    agent_type: str,
    user: dict = Depends(get_current_user),
):
    """获取指定 Agent 类型可用的工具"""
    from app.services.tool_registry import get_tools_for_agent

    user_permissions = user.get("permissions", [])
    tools = get_tools_for_agent(agent_type, user_permissions)

    return ApiResponse(data={
        "agent_type": agent_type,
        "tool_count": len(tools),
        "tools": [t.name for t in tools if hasattr(t, "name")],
    })


@router.post("/tools/refresh", response_model=ApiResponse)
async def refresh_tool_registry(
    user: dict = Depends(get_current_user),
):
    """刷新工具注册表（重新扫描 API 路由）"""
    from app.services.tool_registry import initialize_tools, get_registry_stats

    initialize_tools(force=True)
    stats = get_registry_stats()

    return ApiResponse(data=stats, message="工具注册表已刷新")
