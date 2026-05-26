"""
技能匹配器
根据用户输入匹配最合适的技能
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import re

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_skill import AgentSkill
from .intent_analyzer import IntentAnalysis, IntentType


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill: AgentSkill
    score: float
    match_method: str
    match_details: dict


class SkillMatcher:
    """技能匹配器"""
    
    @staticmethod
    async def find_matching_skills(
        db: AsyncSession,
        intent: IntentAnalysis,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[SkillMatch]:
        """查找匹配的技能"""
        matches: List[SkillMatch] = []
        
        # 1. 关键词精确匹配
        keyword_matches = await SkillMatcher._match_by_keywords(db, intent.keywords)
        for skill, score in keyword_matches:
            matches.append(SkillMatch(
                skill=skill,
                score=score * 0.4,
                match_method="keyword",
                match_details={"keywords": intent.keywords},
            ))
        
        # 2. 意图类型匹配
        intent_matches = await SkillMatcher._match_by_intent(db, intent.intent_type)
        for skill, score in intent_matches:
            # 避免重复
            if not any(m.skill.id == skill.id for m in matches):
                matches.append(SkillMatch(
                    skill=skill,
                    score=score * 0.3,
                    match_method="intent",
                    match_details={"intent_type": intent.intent_type.value},
                ))
            else:
                # 已存在，增加分数
                for m in matches:
                    if m.skill.id == skill.id:
                        m.score += score * 0.2
                        m.match_method = "keyword+intent"
                        break
        
        # 3. 实体匹配
        if intent.entities:
            entity_matches = await SkillMatcher._match_by_entities(db, intent.entities)
            for skill, score in entity_matches:
                if not any(m.skill.id == skill.id for m in matches):
                    matches.append(SkillMatch(
                        skill=skill,
                        score=score * 0.2,
                        match_method="entity",
                        match_details={"entities": intent.entities},
                    ))
                else:
                    for m in matches:
                        if m.skill.id == skill.id:
                            m.score += score * 0.1
                            break
        
        # 4. 触发模式匹配
        if intent.keywords:
            pattern_matches = await SkillMatcher._match_by_patterns(db, intent.keywords)
            for skill, score in pattern_matches:
                if not any(m.skill.id == skill.id for m in matches):
                    matches.append(SkillMatch(
                        skill=skill,
                        score=score * 0.15,
                        match_method="pattern",
                        match_details={"patterns": intent.keywords},
                    ))
                else:
                    for m in matches:
                        if m.skill.id == skill.id:
                            m.score += score * 0.1
                            break
        
        # 5. 应用置信度和使用频率加权
        for match in matches:
            # 置信度加权
            match.score *= match.skill.confidence
            # 使用频率加权（使用越多，分数越高）
            frequency_bonus = min(match.skill.use_count / 100, 0.2)
            match.score += frequency_bonus
        
        # 按分数排序
        matches.sort(key=lambda m: m.score, reverse=True)
        
        # 返回前N个
        return matches[:limit]
    
    @staticmethod
    async def _match_by_keywords(
        db: AsyncSession, 
        keywords: List[str]
    ) -> List[Tuple[AgentSkill, float]]:
        """关键词匹配"""
        if not keywords:
            return []
        
        # 查询包含关键词的技能
        conditions = []
        for keyword in keywords:
            conditions.append(
                or_(
                    AgentSkill.name.ilike(f"%{keyword}%"),
                    AgentSkill.description.ilike(f"%{keyword}%"),
                    AgentSkill.trigger_keywords.any(keyword),
                )
            )
        
        query = select(AgentSkill).where(
            and_(
                AgentSkill.is_active == True,
                or_(*conditions)
            )
        )
        
        result = await db.execute(query)
        skills = result.scalars().all()
        
        # 计算匹配分数
        matches = []
        for skill in skills:
            score = 0.0
            skill_text = f"{skill.name} {skill.description}".lower()
            for keyword in keywords:
                if keyword.lower() in skill_text:
                    score += 0.3
                if skill.trigger_keywords and keyword in skill.trigger_keywords:
                    score += 0.4
            matches.append((skill, min(score, 1.0)))
        
        return matches
    
    @staticmethod
    async def _match_by_intent(
        db: AsyncSession, 
        intent_type: IntentType
    ) -> List[Tuple[AgentSkill, float]]:
        """意图类型匹配"""
        query = select(AgentSkill).where(
            and_(
                AgentSkill.is_active == True,
                AgentSkill.intent_types.any(intent_type.value),
            )
        )
        
        result = await db.execute(query)
        skills = result.scalars().all()
        
        return [(skill, 0.8) for skill in skills]
    
    @staticmethod
    async def _match_by_entities(
        db: AsyncSession, 
        entities: dict
    ) -> List[Tuple[AgentSkill, float]]:
        """实体匹配"""
        if not entities:
            return []
        
        entity_types = list(entities.keys())
        conditions = [
            AgentSkill.category.in_(entity_types),
        ]
        
        query = select(AgentSkill).where(
            and_(
                AgentSkill.is_active == True,
                *conditions,
            )
        )
        
        result = await db.execute(query)
        skills = result.scalars().all()
        
        return [(skill, 0.7) for skill in skills]
    
    @staticmethod
    async def _match_by_patterns(
        db: AsyncSession, 
        keywords: List[str]
    ) -> List[Tuple[AgentSkill, float]]:
        """触发模式匹配"""
        if not keywords:
            return []
        
        # 查询所有启用的技能
        query = select(AgentSkill).where(AgentSkill.is_active == True)
        result = await db.execute(query)
        skills = result.scalars().all()
        
        matches = []
        for skill in skills:
            if not skill.trigger_patterns:
                continue
            
            score = 0.0
            for pattern in skill.trigger_patterns:
                for keyword in keywords:
                    if keyword in pattern or pattern in keyword:
                        score += 0.3
            
            if score > 0:
                matches.append((skill, min(score, 1.0)))
        
        return matches
    
    @staticmethod
    async def record_usage(
        db: AsyncSession,
        skill_id: str,
        success: bool,
        execution_time_ms: int = 0,
    ):
        """记录技能使用"""
        query = select(AgentSkill).where(AgentSkill.id == skill_id)
        result = await db.execute(query)
        skill = result.scalar_one_or_none()
        
        if skill:
            skill.use_count += 1
            if success:
                skill.success_count += 1
            skill.success_rate = skill.success_count / skill.use_count if skill.use_count > 0 else 0
            skill.avg_execution_time = (
                (skill.avg_execution_time * (skill.use_count - 1) + execution_time_ms) / skill.use_count
            )
            await db.commit()
