"""
RAG (检索增强生成) 服务
基于知识库文档的语义检索
"""
import logging
import hashlib
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.agent_model import KnowledgeBase, KnowledgeDocument, AgentConfig

logger = logging.getLogger(__name__)

async def retrieve_relevant_docs(query: str, agent_type: str, top_k: int = 3) -> list[dict]:
    """
    检索与查询相关的知识库文档
    
    策略：
    1. 查找该 Agent 关联的知识库
    2. 在知识库中搜索匹配的文档
    3. 返回最相关的 top_k 个文档片段
    """
    async with AsyncSessionLocal() as session:
        # 1. 获取 Agent 配置，找到关联的知识库
        agent_result = await session.execute(
            select(AgentConfig).where(AgentConfig.agent_type == agent_type)
        )
        agent_config = agent_result.scalar_one_or_none()
        
        if not agent_config or not agent_config.knowledge_base_ids:
            return []
        
        # 2. 在关联的知识库中搜索文档
        relevant_docs = []
        for kb_id in agent_config.knowledge_base_ids:
            # 获取知识库
            kb_result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if not kb:
                continue
            
            # 搜索文档（关键词匹配）
            doc_result = await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.knowledge_base_id == kb_id,
                    KnowledgeDocument.status == "indexed",
                ).limit(20)
            )
            docs = doc_result.scalars().all()
            
            for doc in docs:
                # 简单的关键词匹配评分
                score = _calculate_relevance(query, doc.filename, getattr(doc, 'content', ''))
                if score > 0:
                    relevant_docs.append({
                        "kb_name": kb.name,
                        "doc_id": str(doc.id),
                        "filename": doc.filename,
                        "content": getattr(doc, 'content', '')[:2000],  # 限制长度
                        "score": score,
                    })
        
        # 3. 按相关性排序，返回 top_k
        relevant_docs.sort(key=lambda x: x["score"], reverse=True)
        return relevant_docs[:top_k]


def _calculate_relevance(query: str, title: str, content: str) -> float:
    """简单的关键词匹配相关性评分"""
    query_lower = query.lower()
    title_lower = title.lower() if title else ""
    content_lower = content.lower() if content else ""
    
    score = 0.0
    
    # 标题匹配（权重更高）
    query_words = set(query_lower.split())
    for word in query_words:
        if word in title_lower:
            score += 2.0
        if word in content_lower:
            score += 1.0
    
    return score


def build_rag_context(query: str, agent_type: str) -> str:
    """
    构建 RAG 上下文（同步版本，用于 Agent 调用）
    返回相关文档的格式化文本
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已在运行，创建任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, retrieve_relevant_docs(query, agent_type))
                docs = future.result(timeout=10)
        else:
            docs = loop.run_until_complete(retrieve_relevant_docs(query, agent_type))
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return ""
    
    if not docs:
        return ""
    
    # 格式化上下文
    context_parts = ["以下是从知识库中检索到的相关信息：\n"]
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"【文档{i}】{doc['filename']}（知识库：{doc['kb_name']}）")
        if doc['content']:
            context_parts.append(doc['content'][:1500])
        context_parts.append("")
    
    return "\n".join(context_parts)