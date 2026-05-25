"""
RAG (检索增强生成) 服务 — 增强版
=================================
改进检索逻辑：
- 分块策略：长文档按段落分块（chunk_size=512, overlap=128）
- 多字段匹配：同时匹配标题、内容、标签、摘要
- 权重评分：标题3.0 / 标签2.5 / 摘要2.0 / 内容1.0
- 结果重排序：相关性 + 新鲜度 + 质量分综合排序
- 缓存机制：相同查询结果缓存5分钟
"""
import time
import logging
import hashlib
import re
from typing import Optional
from collections import OrderedDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.agent_model import KnowledgeBase, KnowledgeDocument, AgentConfig

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

CHUNK_SIZE = 512          # 分块大小（字符数）
CHUNK_OVERLAP = 128       # 分块重叠（字符数）
CACHE_TTL = 300           # 缓存过期时间（秒）
CACHE_MAX_SIZE = 256      # 缓存最大条目数

# 字段权重
FIELD_WEIGHTS = {
    "title": 3.0,
    "tags": 2.5,
    "summary": 2.0,
    "content": 1.0,
}

# 重排序权重
RERANK_WEIGHTS = {
    "relevance": 0.6,     # 相关性权重
    "freshness": 0.25,    # 新鲜度权重
    "quality": 0.15,      # 质量分权重
}

# ==================== 缓存 ====================

_rag_cache: OrderedDict[str, tuple[float, list]] = OrderedDict()


def _cache_key(query: str, agent_type: str, top_k: int) -> str:
    """生成缓存键"""
    raw = f"{query}|{agent_type}|{top_k}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[list]:
    """从缓存获取结果"""
    if key in _rag_cache:
        ts, data = _rag_cache[key]
        if time.time() - ts < CACHE_TTL:
            # 移到末尾（LRU）
            _rag_cache.move_to_end(key)
            return data
        else:
            del _rag_cache[key]
    return None


def _set_cache(key: str, data: list):
    """设置缓存"""
    _rag_cache[key] = (time.time(), data)
    # LRU 淘汰
    while len(_rag_cache) > CACHE_MAX_SIZE:
        _rag_cache.popitem(last=False)


# ==================== 文档分块 ====================

def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    将长文本按段落分块，支持重叠
    优先按段落分割，段落过长时按句子分割
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    # 先按段落分割
    paragraphs = re.split(r'\n{2,}', text)

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 段落本身过长时，按句子分割
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[。！？.!?])', para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) <= chunk_size:
                        sub_chunk += sent
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                # 添加重叠
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ==================== 多字段匹配评分 ====================

def _calculate_weighted_score(query: str, title: str, content: str,
                               tags: str = "", summary: str = "") -> float:
    """
    多字段加权匹配评分
    - 标题匹配权重 3.0
    - 标签匹配权重 2.5
    - 摘要匹配权重 2.0
    - 内容匹配权重 1.0
    """
    query_lower = query.lower()
    # 提取查询关键词（中文按字/词切分，英文按空格切分）
    query_terms = _extract_terms(query_lower)
    if not query_terms:
        return 0.0

    score = 0.0

    # 标题匹配
    title_lower = (title or "").lower()
    title_hits = sum(1 for t in query_terms if t in title_lower)
    score += (title_hits / len(query_terms)) * FIELD_WEIGHTS["title"]

    # 标签匹配
    tags_lower = (tags or "").lower()
    tag_list = [t.strip() for t in re.split(r'[,;，；\s]+', tags_lower) if t.strip()]
    tag_hits = sum(1 for t in query_terms if any(t in tag for tag in tag_list))
    score += (tag_hits / len(query_terms)) * FIELD_WEIGHTS["tags"]

    # 摘要匹配
    summary_lower = (summary or "").lower()
    summary_hits = sum(1 for t in query_terms if t in summary_lower)
    score += (summary_hits / len(query_terms)) * FIELD_WEIGHTS["summary"]

    # 内容匹配
    content_lower = (content or "").lower()
    content_hits = sum(1 for t in query_terms if t in content_lower)
    score += (content_hits / len(query_terms)) * FIELD_WEIGHTS["content"]

    return score


def _extract_terms(text: str) -> list[str]:
    """提取查询关键词"""
    # 英文单词
    en_words = re.findall(r'[a-z]+', text)
    # 中文连续字符（2-4字组合）
    cn_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    cn_terms = []
    for seg in cn_chars:
        # 2字组合
        for i in range(len(seg) - 1):
            cn_terms.append(seg[i:i+2])
        # 3字组合
        for i in range(len(seg) - 2):
            cn_terms.append(seg[i:i+3])
        # 完整段
        cn_terms.append(seg)

    all_terms = en_words + cn_terms
    return list(set(all_terms)) if all_terms else [text]


# ==================== 结果重排序 ====================

def _rerank_results(docs: list[dict]) -> list[dict]:
    """
    基于相关性 + 新鲜度 + 质量分综合重排序
    """
    if not docs:
        return docs

    # 归一化各维度分数
    max_relevance = max(d.get("relevance_score", 0) for d in docs) or 1.0
    max_age_hours = max(d.get("age_hours", 0) for d in docs) or 1.0

    for doc in docs:
        # 相关性分（归一化）
        rel_norm = doc.get("relevance_score", 0) / max_relevance

        # 新鲜度分（越新越高，线性衰减）
        age_hours = doc.get("age_hours", 0)
        freshness = 1.0 - (age_hours / max_age_hours) if max_age_hours > 0 else 1.0

        # 质量分（直接使用，归一化到 0-1）
        quality = min(doc.get("quality_score", 0.5), 1.0)

        # 综合得分
        doc["final_score"] = (
            RERANK_WEIGHTS["relevance"] * rel_norm +
            RERANK_WEIGHTS["freshness"] * freshness +
            RERANK_WEIGHTS["quality"] * quality
        )

    docs.sort(key=lambda x: x["final_score"], reverse=True)
    return docs


# ==================== 主检索函数 ====================

async def retrieve_relevant_docs(query: str, agent_type: str, top_k: int = 3) -> list[dict]:
    """
    检索与查询相关的知识库文档（增强版）

    策略：
    1. 查找该 Agent 关联的知识库
    2. 多字段加权匹配（标题/标签/摘要/内容）
    3. 文档分块处理
    4. 结果重排序（相关性+新鲜度+质量分）
    5. 缓存机制（5分钟TTL）
    """
    # 检查缓存
    cache_k = _cache_key(query, agent_type, top_k)
    cached = _get_cached(cache_k)
    if cached is not None:
        logger.debug(f"RAG cache hit for query: {query[:50]}")
        return cached

    async with AsyncSessionLocal() as session:
        # 1. 获取 Agent 配置，找到关联的知识库
        agent_result = await session.execute(
            select(AgentConfig).where(AgentConfig.agent_type == agent_type)
        )
        agent_config = agent_result.scalar_one_or_none()

        if not agent_config or not agent_config.knowledge_base_ids:
            return []

        # 2. 在关联的知识库中搜索文档
        all_chunks = []
        for kb_id in agent_config.knowledge_base_ids:
            kb_result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if not kb:
                continue

            doc_result = await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.knowledge_base_id == kb_id,
                    KnowledgeDocument.status == "indexed",
                ).limit(50)
            )
            docs = doc_result.scalars().all()

            for doc in docs:
                title = doc.filename or ""
                content = getattr(doc, 'content', '') or ""
                tags = getattr(doc, 'tags', '') or ""
                summary = getattr(doc, 'summary', '') or ""
                quality_score = getattr(doc, 'quality_score', 0.5) or 0.5
                created_at = getattr(doc, 'created_at', None)

                # 计算文档年龄（小时）
                age_hours = 0.0
                if created_at:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    if created_at.tzinfo is None:
                        from datetime import timezone as tz
                        created_at = created_at.replace(tzinfo=tz.utc)
                    age_hours = max((now - created_at).total_seconds() / 3600, 0)

                # 多字段加权评分
                relevance_score = _calculate_weighted_score(query, title, content, tags, summary)

                if relevance_score <= 0:
                    continue

                # 文档分块
                chunks = _chunk_text(content)
                if not chunks:
                    chunks = [content[:CHUNK_SIZE]] if content else []

                for i, chunk in enumerate(chunks):
                    chunk_score = _calculate_weighted_score(query, title, chunk, tags, summary)
                    # 首块（通常包含摘要）给予额外加成
                    if i == 0:
                        chunk_score *= 1.2

                    all_chunks.append({
                        "kb_name": kb.name,
                        "doc_id": str(doc.id),
                        "filename": title,
                        "chunk_index": i,
                        "content": chunk[:1500],
                        "tags": tags,
                        "summary": summary[:500] if summary else "",
                        "relevance_score": chunk_score,
                        "age_hours": age_hours,
                        "quality_score": quality_score,
                    })

    # 3. 重排序
    all_chunks = _rerank_results(all_chunks)

    # 4. 取 top_k（同一文档最多取2个块，避免重复）
    result = []
    doc_chunk_count: dict[str, int] = {}
    for chunk in all_chunks:
        doc_id = chunk["doc_id"]
        if doc_chunk_count.get(doc_id, 0) >= 2:
            continue
        doc_chunk_count[doc_id] = doc_chunk_count.get(doc_id, 0) + 1
        result.append(chunk)
        if len(result) >= top_k:
            break

    # 写入缓存
    _set_cache(cache_k, result)

    return result


def build_rag_context(query: str, agent_type: str) -> str:
    """
    构建 RAG 上下文（同步版本，用于 Agent 调用）
    返回相关文档的格式化文本
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
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
        context_parts.append(f"【文档{i}】{doc['filename']}（知识库：{doc['kb_name']}，相关度：{doc.get('final_score', 0):.2f}）")
        if doc.get('summary'):
            context_parts.append(f"摘要：{doc['summary']}")
        if doc.get('tags'):
            context_parts.append(f"标签：{doc['tags']}")
        if doc['content']:
            context_parts.append(doc['content'][:1500])
        context_parts.append("")

    return "\n".join(context_parts)


def clear_rag_cache():
    """清空 RAG 缓存"""
    _rag_cache.clear()
    logger.info("RAG cache cleared")


def get_cache_stats() -> dict:
    """获取缓存统计"""
    valid = sum(1 for ts, _ in _rag_cache.values() if time.time() - ts < CACHE_TTL)
    return {
        "total_entries": len(_rag_cache),
        "valid_entries": valid,
        "cache_ttl_seconds": CACHE_TTL,
        "cache_max_size": CACHE_MAX_SIZE,
    }
