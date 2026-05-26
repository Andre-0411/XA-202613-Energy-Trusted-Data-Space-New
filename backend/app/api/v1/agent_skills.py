"""
Agent 技能 API
支持技能的查询、创建、学习和调用
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent_skill import AgentSkill, SkillExecutionLog, UserPreference
from app.services.agent_skills import SkillManager, IntentAnalyzer

router = APIRouter()


# ===== 请求/响应模型 =====

class SkillCreate(BaseModel):
    name: str = Field(..., description="技能名称")
    description: str = Field(..., description="技能描述")
    category: str = Field(default="general", description="技能类别")
    instructions: str = Field(..., description="执行指令")
    trigger_keywords: List[str] = Field(default=[], description="触发关键词")
    intent_types: List[str] = Field(default=[], description="意图类型")
    examples: Optional[Dict] = Field(default=None, description="示例")
    parameters: Optional[Dict] = Field(default=None, description="参数定义")

class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    instructions: str
    trigger_keywords: List[str]
    intent_types: List[str]
    use_count: int
    success_rate: float
    confidence: float
    source: str
    is_active: bool
    is_verified: bool
    created_at: datetime

class ProcessMessageRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(default=None, description="会话ID")

class LearnSkillRequest(BaseModel):
    user_input: str = Field(..., description="用户输入")
    assistant_response: str = Field(..., description="助手回复")
    conversation_id: Optional[str] = Field(default=None, description="会话ID")

class ExecuteSkillRequest(BaseModel):
    skill_id: str = Field(..., description="技能ID")
    user_input: str = Field(..., description="用户输入")
    parameters: Optional[Dict] = Field(default=None, description="执行参数")


# ===== API 端点 =====

@router.get("/", summary="获取技能列表")
async def list_skills(
    category: Optional[str] = Query(None, description="类别筛选"),
    source: Optional[str] = Query(None, description="来源筛选"),
    is_active: bool = Query(True, description="是否启用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取技能列表"""
    query = select(AgentSkill).where(AgentSkill.is_active == is_active)
    
    if category:
        query = query.where(AgentSkill.category == category)
    if source:
        query = query.where(AgentSkill.source == source)
    
    # 获取总数
    from sqlalchemy import func
    count_query = select(func.count()).select_from(AgentSkill).where(AgentSkill.is_active == is_active)
    if category:
        count_query = count_query.where(AgentSkill.category == category)
    if source:
        count_query = count_query.where(AgentSkill.source == source)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    query = query.order_by(AgentSkill.use_count.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    skills = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "trigger_keywords": s.trigger_keywords or [],
                "intent_types": s.intent_types or [],
                "use_count": s.use_count,
                "success_rate": s.success_rate,
                "confidence": s.confidence,
                "source": s.source,
                "is_active": s.is_active,
                "is_verified": s.is_verified,
            }
            for s in skills
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/", summary="创建技能")
async def create_skill(
    request: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """手动创建技能"""
    # 检查名称唯一性
    existing = await db.execute(
        select(AgentSkill).where(AgentSkill.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="技能名称已存在")
    
    skill = AgentSkill(
        name=request.name,
        description=request.description,
        category=request.category,
        instructions=request.instructions,
        trigger_keywords=request.trigger_keywords,
        intent_types=request.intent_types,
        examples=request.examples,
        parameters=request.parameters,
        source="manual",
        confidence=0.8,
        is_active=True,
        is_verified=True,
    )
    
    db.add(skill)
    await db.commit()
    
    return {"message": "技能创建成功", "skill_id": str(skill.id)}


@router.post("/process", summary="处理用户消息")
async def process_message(
    request: ProcessMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """处理用户消息，返回技能匹配结果"""
    user_id = current_user.get("user_id") or current_user.get("sub")
    
    manager = SkillManager(db)
    result = await manager.process_message(
        request.message,
        user_id=user_id,
        conversation_id=request.conversation_id,
    )
    
    return result


@router.post("/learn", summary="从对话学习技能")
async def learn_skill(
    request: LearnSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """从对话中学习新技能"""
    user_id = current_user.get("user_id") or current_user.get("sub")
    
    manager = SkillManager(db)
    result = await manager.learn_skill_from_conversation(
        request.user_input,
        request.assistant_response,
        user_id=user_id,
        conversation_id=request.conversation_id,
    )
    
    if result:
        return {"learned": True, "skill": result}
    else:
        return {"learned": False, "reason": "交互不满足学习条件"}


@router.post("/execute", summary="执行技能")
async def execute_skill(
    request: ExecuteSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """执行指定技能"""
    user_id = current_user.get("user_id") or current_user.get("sub")
    
    manager = SkillManager(db)
    result = await manager.execute_skill(
        request.skill_id,
        request.user_input,
        user_id=user_id,
        parameters=request.parameters,
    )
    
    return result


@router.get("/statistics", summary="获取技能统计")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取技能使用统计"""
    manager = SkillManager(db)
    return await manager.get_skill_statistics()


@router.get("/{skill_id}", summary="获取技能详情")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取技能详情"""
    query = select(AgentSkill).where(AgentSkill.id == skill_id)
    result = await db.execute(query)
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    return {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "instructions": skill.instructions,
        "trigger_keywords": skill.trigger_keywords or [],
        "intent_types": skill.intent_types or [],
        "examples": skill.examples,
        "parameters": skill.parameters,
        "use_count": skill.use_count,
        "success_count": skill.success_count,
        "success_rate": skill.success_rate,
        "avg_execution_time": skill.avg_execution_time,
        "confidence": skill.confidence,
        "source": skill.source,
        "learned_from": skill.learned_from,
        "is_active": skill.is_active,
        "is_verified": skill.is_verified,
        "version": skill.version,
        "tags": skill.tags or [],
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
    }


@router.put("/{skill_id}", summary="更新技能")
async def update_skill(
    skill_id: str,
    request: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新技能"""
    query = select(AgentSkill).where(AgentSkill.id == skill_id)
    result = await db.execute(query)
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill.name = request.name
    skill.description = request.description
    skill.category = request.category
    skill.instructions = request.instructions
    skill.trigger_keywords = request.trigger_keywords
    skill.intent_types = request.intent_types
    skill.examples = request.examples
    skill.parameters = request.parameters
    skill.version += 1
    
    await db.commit()
    
    return {"message": "技能更新成功"}


@router.delete("/{skill_id}", summary="删除技能")
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除技能"""
    query = select(AgentSkill).where(AgentSkill.id == skill_id)
    result = await db.execute(query)
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    # 软删除
    skill.is_active = False
    await db.commit()
    
    return {"message": "技能已禁用"}


@router.get("/{skill_id}/logs", summary="获取技能执行日志")
async def get_skill_logs(
    skill_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取技能执行日志"""
    query = select(SkillExecutionLog).where(
        SkillExecutionLog.skill_id == skill_id
    ).order_by(SkillExecutionLog.created_at.desc())
    
    from sqlalchemy import func
    count_query = select(func.count()).select_from(SkillExecutionLog).where(
        SkillExecutionLog.skill_id == skill_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(log.id),
                "input_text": log.input_text,
                "output_text": log.output_text,
                "execution_time_ms": log.execution_time_ms,
                "success": log.success,
                "error_message": log.error_message,
                "match_score": log.match_score,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
