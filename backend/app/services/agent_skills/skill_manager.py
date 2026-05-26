"""
技能管理器
负责技能的创建、学习、检索和调用
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import re

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_skill import AgentSkill, SkillExecutionLog, UserPreference
from .intent_analyzer import IntentAnalyzer, IntentType, IntentAnalysis
from .skill_matcher import SkillMatcher, SkillMatch


class SkillManager:
    """技能管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_message(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理用户消息，返回技能匹配结果和建议"""
        
        # 1. 分析意图
        intent = IntentAnalyzer.analyze(user_input)
        
        # 2. 查找匹配的技能
        matches = await SkillMatcher.find_matching_skills(
            self.db, intent, user_id, limit=3
        )
        
        # 3. 获取用户偏好
        preferences = await self._get_user_preferences(user_id) if user_id else {}
        
        # 4. 构建响应
        result = {
            "intent": {
                "type": intent.intent_type.value,
                "confidence": intent.confidence,
                "keywords": intent.keywords,
                "entities": intent.entities,
                "action": intent.action,
                "target": intent.target,
            },
            "matched_skills": [],
            "suggestions": [],
            "user_preferences": preferences,
        }
        
        # 添加匹配的技能
        for match in matches:
            result["matched_skills"].append({
                "id": str(match.skill.id),
                "name": match.skill.name,
                "description": match.skill.description,
                "category": match.skill.category,
                "score": round(match.score, 3),
                "match_method": match.match_method,
                "confidence": match.skill.confidence,
                "use_count": match.skill.use_count,
            })
        
        # 5. 生成建议
        if not matches:
            result["suggestions"] = await self._generate_suggestions(intent)
        
        return result
    
    async def execute_skill(
        self,
        skill_id: str,
        user_input: str,
        user_id: Optional[str] = None,
        parameters: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """执行技能"""
        start_time = datetime.now()
        
        # 获取技能
        query = select(AgentSkill).where(AgentSkill.id == skill_id)
        result = await self.db.execute(query)
        skill = result.scalar_one_or_none()
        
        if not skill:
            return {"success": False, "error": "技能不存在"}
        
        try:
            # 执行技能指令
            output = await self._execute_skill_instructions(
                skill, user_input, parameters or {}
            )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 记录执行日志
            log = SkillExecutionLog(
                skill_id=skill.id,
                user_id=user_id,
                input_text=user_input,
                output_text=str(output),
                execution_time_ms=execution_time,
                success=True,
                match_score=1.0,
                match_method="direct",
            )
            self.db.add(log)
            
            # 更新使用统计
            await SkillMatcher.record_usage(self.db, str(skill.id), True, execution_time)
            
            await self.db.commit()
            
            return {
                "success": True,
                "skill_name": skill.name,
                "output": output,
                "execution_time_ms": execution_time,
            }
            
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 记录失败
            log = SkillExecutionLog(
                skill_id=skill.id,
                user_id=user_id,
                input_text=user_input,
                error_message=str(e),
                execution_time_ms=execution_time,
                success=False,
            )
            self.db.add(log)
            await SkillMatcher.record_usage(self.db, str(skill.id), False, execution_time)
            await self.db.commit()
            
            return {"success": False, "error": str(e)}
    
    async def learn_skill_from_conversation(
        self,
        user_input: str,
        assistant_response: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """从对话中学习新技能"""
        
        # 1. 分析对话
        intent = IntentAnalyzer.analyze(user_input)
        
        # 2. 判断是否值得学习
        if not self._should_learn(intent, assistant_response):
            return None
        
        # 3. 提取技能信息
        skill_info = self._extract_skill_info(user_input, assistant_response, intent)
        
        # 4. 检查是否已存在类似技能
        existing = await self._find_similar_skill(skill_info["name"], skill_info["keywords"])
        if existing:
            # 更新现有技能
            return await self._update_existing_skill(existing, skill_info)
        
        # 5. 创建新技能
        return await self._create_new_skill(skill_info, user_id, conversation_id)
    
    def _should_learn(self, intent: IntentAnalysis, response: str) -> bool:
        """判断是否应该学习这个交互"""
        # 不学习通用对话
        if intent.intent_type == IntentType.GENERAL:
            return False
        
        # 不学习太短的交互
        if len(response) < 50:
            return False
        
        # 不学习低置信度的意图
        if intent.confidence < 0.4:
            return False
        
        return True
    
    def _extract_skill_info(
        self, 
        user_input: str, 
        response: str, 
        intent: IntentAnalysis
    ) -> Dict[str, Any]:
        """从对话中提取技能信息"""
        
        # 生成技能名称
        name = self._generate_skill_name(user_input, intent)
        
        # 生成技能描述
        description = self._generate_skill_description(user_input, intent)
        
        # 提取关键词
        keywords = intent.keywords.copy()
        
        # 确定类别
        category = IntentAnalyzer.get_skill_category(intent.intent_type, intent.entities)
        
        # 生成指令
        instructions = self._generate_instructions(user_input, response, intent)
        
        return {
            "name": name,
            "description": description,
            "category": category,
            "instructions": instructions,
            "trigger_keywords": keywords,
            "intent_types": [intent.intent_type.value],
            "entities": intent.entities,
        }
    
    def _generate_skill_name(self, user_input: str, intent: IntentAnalysis) -> str:
        """生成技能名称"""
        action_map = {
            "query": "查询",
            "create": "创建",
            "update": "更新",
            "delete": "删除",
            "analyze": "分析",
        }
        
        action = action_map.get(intent.action, "处理")
        target = intent.target or "数据"
        
        return f"{action}{target}"
    
    def _generate_skill_description(self, user_input: str, intent: IntentAnalysis) -> str:
        """生成技能描述"""
        return f"处理用户关于{intent.target or '数据'}的{intent.intent_type.value}请求"
    
    def _generate_instructions(
        self, 
        user_input: str, 
        response: str, 
        intent: IntentAnalysis
    ) -> str:
        """生成技能执行指令"""
        # 从响应中提取执行步骤
        steps = []
        
        # 分析响应中的步骤
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+[\.\)、]', line):
                steps.append(line)
            elif line.startswith('- ') or line.startswith('* '):
                steps.append(line)
        
        if steps:
            return '\n'.join(steps)
        
        # 默认指令
        return f"根据用户输入执行{intent.intent_type.value}操作"
    
    async def _find_similar_skill(
        self, 
        name: str, 
        keywords: List[str]
    ) -> Optional[AgentSkill]:
        """查找相似的技能"""
        query = select(AgentSkill).where(
            or_(
                AgentSkill.name.ilike(f"%{name}%"),
                AgentSkill.trigger_keywords.overlap(keywords),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _update_existing_skill(
        self, 
        skill: AgentSkill, 
        skill_info: Dict
    ) -> Dict[str, Any]:
        """更新现有技能"""
        # 合并关键词
        existing_keywords = set(skill.trigger_keywords or [])
        new_keywords = set(skill_info["trigger_keywords"])
        skill.trigger_keywords = list(existing_keywords | new_keywords)
        
        # 更新置信度
        skill.confidence = min(skill.confidence + 0.1, 1.0)
        skill.version += 1
        
        await self.db.commit()
        
        return {
            "action": "updated",
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "new_confidence": skill.confidence,
        }
    
    async def _create_new_skill(
        self, 
        skill_info: Dict, 
        user_id: Optional[str],
        conversation_id: Optional[str]
    ) -> Dict[str, Any]:
        """创建新技能"""
        skill = AgentSkill(
            name=skill_info["name"],
            description=skill_info["description"],
            category=skill_info["category"],
            instructions=skill_info["instructions"],
            trigger_keywords=skill_info["trigger_keywords"],
            intent_types=skill_info["intent_types"],
            source="learned",
            learned_from=conversation_id,
            confidence=0.5,
            is_active=True,
            is_verified=False,
        )
        
        self.db.add(skill)
        await self.db.commit()
        
        return {
            "action": "created",
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "category": skill.category,
        }
    
    async def _generate_suggestions(self, intent: IntentAnalysis) -> List[str]:
        """生成建议"""
        suggestions = []
        
        if intent.intent_type == IntentType.QUERY:
            suggestions.append("您可以尝试更具体的查询条件")
            suggestions.append("试试使用筛选功能缩小范围")
        elif intent.intent_type == IntentType.CREATE:
            suggestions.append("请提供必要的创建参数")
            suggestions.append("您可以先查看现有资源避免重复")
        elif intent.intent_type == IntentType.TROUBLESHOOT:
            suggestions.append("请提供详细的错误信息")
            suggestions.append("您可以查看系统日志获取更多信息")
        
        return suggestions
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
        query = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.db.execute(query)
        preferences = result.scalars().all()
        
        pref_dict = {}
        for pref in preferences:
            if pref.preference_type not in pref_dict:
                pref_dict[pref.preference_type] = {}
            pref_dict[pref.preference_type][pref.preference_key] = {
                "value": pref.preference_value,
                "confidence": pref.confidence,
            }
        
        return pref_dict
    
    async def get_skill_statistics(self) -> Dict[str, Any]:
        """获取技能统计"""
        # 总技能数
        total_query = select(func.count()).select_from(AgentSkill)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0
        
        # 按类别统计
        category_query = select(
            AgentSkill.category,
            func.count(),
            func.avg(AgentSkill.success_rate),
        ).group_by(AgentSkill.category)
        category_result = await self.db.execute(category_query)
        categories = {row[0]: {"count": row[1], "avg_success_rate": row[2]} 
                     for row in category_result.all()}
        
        # 按来源统计
        source_query = select(
            AgentSkill.source,
            func.count(),
        ).group_by(AgentSkill.source)
        source_result = await self.db.execute(source_query)
        sources = {row[0]: row[1] for row in source_result.all()}
        
        # 最常用技能
        top_query = select(AgentSkill).order_by(AgentSkill.use_count.desc()).limit(5)
        top_result = await self.db.execute(top_query)
        top_skills = [
            {"name": s.name, "use_count": s.use_count, "success_rate": s.success_rate}
            for s in top_result.scalars().all()
        ]
        
        return {
            "total_skills": total,
            "by_category": categories,
            "by_source": sources,
            "top_skills": top_skills,
        }
