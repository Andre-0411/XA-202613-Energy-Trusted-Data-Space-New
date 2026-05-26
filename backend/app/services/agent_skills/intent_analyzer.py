"""
意图分析器
分析用户输入，识别意图类型和关键信息
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举"""
    QUERY = "query"           # 查询类
    CREATE = "create"         # 创建类
    UPDATE = "update"         # 更新类
    DELETE = "delete"         # 删除类
    ANALYZE = "analyze"       # 分析类
    EXPLAIN = "explain"       # 解释类
    COMPARE = "compare"       # 比较类
    RECOMMEND = "recommend"   # 推荐类
    TROUBLESHOOT = "troubleshoot"  # 排障类
    AUTOMATE = "automate"     # 自动化类
    LEARN = "learn"           # 学习类
    GENERAL = "general"       # 通用类


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    intent_type: IntentType
    confidence: float
    keywords: List[str]
    entities: Dict[str, str]
    action: Optional[str]
    target: Optional[str]
    modifiers: List[str]


class IntentAnalyzer:
    """意图分析器"""
    
    # 意图模式定义
    INTENT_PATTERNS = {
        IntentType.QUERY: {
            "patterns": [
                r"(查询|查找|搜索|获取|查看|列出|显示|看看|找找)",
                r"(什么|哪些|多少|几个|怎么|如何|哪里)",
                r"(有没有|是否存在|是否)",
            ],
            "keywords": ["查询", "查找", "搜索", "获取", "查看", "列表", "详情"],
        },
        IntentType.CREATE: {
            "patterns": [
                r"(创建|新建|添加|增加|生成|建立|注册|发布)",
                r"(帮我|请|麻烦).*(创建|新建|添加)",
            ],
            "keywords": ["创建", "新建", "添加", "增加", "生成", "发布"],
        },
        IntentType.UPDATE: {
            "patterns": [
                r"(更新|修改|编辑|变更|调整|改动)",
                r"(把|将|让).*(改成|改为|更新为)",
            ],
            "keywords": ["更新", "修改", "编辑", "变更", "调整"],
        },
        IntentType.DELETE: {
            "patterns": [
                r"(删除|移除|取消|禁用|停用|注销)",
            ],
            "keywords": ["删除", "移除", "取消", "禁用"],
        },
        IntentType.ANALYZE: {
            "patterns": [
                r"(分析|统计|汇总|计算|评估|诊断)",
                r"(趋势|对比|差异|变化|波动)",
            ],
            "keywords": ["分析", "统计", "汇总", "计算", "评估"],
        },
        IntentType.EXPLAIN: {
            "patterns": [
                r"(解释|说明|介绍|什么是|是什么|含义|意思)",
                r"(为什么|为何|原因|原理|机制)",
            ],
            "keywords": ["解释", "说明", "介绍", "什么是", "为什么"],
        },
        IntentType.COMPARE: {
            "patterns": [
                r"(比较|对比|区别|差异|哪个更|哪个好)",
                r"(vs|versus|和.*比|与.*比)",
            ],
            "keywords": ["比较", "对比", "区别", "差异"],
        },
        IntentType.RECOMMEND: {
            "patterns": [
                r"(推荐|建议|应该|适合|最好|最优)",
                r"(怎么选|如何选择|选哪个)",
            ],
            "keywords": ["推荐", "建议", "应该", "适合", "最优"],
        },
        IntentType.TROUBLESHOOT: {
            "patterns": [
                r"(报错|错误|失败|异常|问题|故障|bug|issue)",
                r"(不能|无法|不行|不了|不起作用)",
                r"(解决|修复|排查|调试)",
            ],
            "keywords": ["报错", "错误", "失败", "异常", "问题", "解决"],
        },
        IntentType.AUTOMATE: {
            "patterns": [
                r"(自动化|定时|定期|批量|一键|自动)",
                r"(每天|每周|每月|每小时|定时)",
            ],
            "keywords": ["自动化", "定时", "批量", "自动"],
        },
        IntentType.LEARN: {
            "patterns": [
                r"(学习|教程|入门|进阶|掌握|了解)",
                r"(怎么用|如何使用|使用方法|操作步骤)",
            ],
            "keywords": ["学习", "教程", "入门", "怎么用"],
        },
    }
    
    # 实体模式
    ENTITY_PATTERNS = {
        "data_asset": r"(数据资产|数据集|数据源|数据资源)",
        "compute_task": r"(计算任务|训练任务|联邦学习|FL任务)",
        "blockchain": r"(区块链|NFT|上链|存证|智能合约)",
        "user": r"(用户|账号|账户|管理员)",
        "organization": r"(组织|机构|企业|单位)",
        "security": r"(安全|权限|密钥|证书|MFA)",
        "mfa": r"(MFA|多因素认证|二次验证|TOTP)",
        "websocket": r"(WebSocket|实时通知|推送|WS)",
    }
    
    @classmethod
    def analyze(cls, text: str) -> IntentAnalysis:
        """分析用户输入的意图"""
        text_lower = text.lower().strip()
        
        # 1. 匹配意图类型
        intent_scores: Dict[IntentType, float] = {}
        matched_keywords: List[str] = []
        
        for intent_type, config in cls.INTENT_PATTERNS.items():
            score = 0.0
            for pattern in config["patterns"]:
                if re.search(pattern, text):
                    score += 0.4
            for keyword in config["keywords"]:
                if keyword in text:
                    score += 0.2
                    matched_keywords.append(keyword)
            if score > 0:
                intent_scores[intent_type] = min(score, 1.0)
        
        # 选择最高分的意图
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
        else:
            best_intent = IntentType.GENERAL
            confidence = 0.3
        
        # 2. 提取实体
        entities = {}
        for entity_type, pattern in cls.ENTITY_PATTERNS.items():
            if re.search(pattern, text):
                entities[entity_type] = re.search(pattern, text).group()
        
        # 3. 提取动作和目标
        action = cls._extract_action(text)
        target = cls._extract_target(text)
        
        # 4. 提取修饰词
        modifiers = cls._extract_modifiers(text)
        
        return IntentAnalysis(
            intent_type=best_intent,
            confidence=confidence,
            keywords=list(set(matched_keywords)),
            entities=entities,
            action=action,
            target=target,
            modifiers=modifiers,
        )
    
    @classmethod
    def _extract_action(cls, text: str) -> Optional[str]:
        """提取动作"""
        action_patterns = [
            (r"(查询|查找|搜索|获取|查看)", "query"),
            (r"(创建|新建|添加|生成)", "create"),
            (r"(更新|修改|编辑|变更)", "update"),
            (r"(删除|移除|取消)", "delete"),
            (r"(分析|统计|计算|评估)", "analyze"),
            (r"(导出|下载|发送)", "export"),
            (r"(导入|上传|提交)", "import"),
            (r"(启用|禁用|激活|停用)", "toggle"),
        ]
        for pattern, action in action_patterns:
            if re.search(pattern, text):
                return action
        return None
    
    @classmethod
    def _extract_target(cls, text: str) -> Optional[str]:
        """提取目标对象"""
        target_patterns = [
            (r"(数据资产|数据集|数据源)", "data_asset"),
            (r"(计算任务|训练任务)", "compute_task"),
            (r"(用户|账号)", "user"),
            (r"(组织|机构)", "organization"),
            (r"(NFT|存证|区块链)", "blockchain"),
            (r"(安全|密钥|证书)", "security"),
            (r"(MFA|多因素认证)", "mfa"),
        ]
        for pattern, target in target_patterns:
            if re.search(pattern, text):
                return target
        return None
    
    @classmethod
    def _extract_modifiers(cls, text: str) -> List[str]:
        """提取修饰词"""
        modifiers = []
        modifier_patterns = [
            (r"(最近|近期)", "recent"),
            (r"(全部|所有|所有)", "all"),
            (r"(前\d+个|前\d+条)", "top_n"),
            (r"(按.*排序|排序)", "sorted"),
            (r"(降序|升序|从大到小|从小到大)", "order"),
            (r"(今天|昨天|本周|本月)", "time_range"),
        ]
        for pattern, modifier in modifier_patterns:
            if re.search(pattern, text):
                modifiers.append(modifier)
        return modifiers
    
    @classmethod
    def get_skill_category(cls, intent_type: IntentType, entities: Dict[str, str]) -> str:
        """根据意图和实体确定技能类别"""
        # 优先使用实体类型作为类别
        if entities:
            return list(entities.keys())[0]
        
        # 否则使用意图类型
        category_mapping = {
            IntentType.QUERY: "data_query",
            IntentType.CREATE: "resource_management",
            IntentType.UPDATE: "resource_management",
            IntentType.DELETE: "resource_management",
            IntentType.ANALYZE: "data_analysis",
            IntentType.EXPLAIN: "knowledge",
            IntentType.COMPARE: "data_analysis",
            IntentType.RECOMMEND: "decision_support",
            IntentType.TROUBLESHOOT: "troubleshooting",
            IntentType.AUTOMATE: "automation",
            IntentType.LEARN: "knowledge",
        }
        return category_mapping.get(intent_type, "general")
