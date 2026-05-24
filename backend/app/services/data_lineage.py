"""
数据血缘追踪服务
================
记录数据从采集→处理→使用的完整生命周期
支持 ECharts 关系图可视化
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    """血缘节点"""
    node_id: str
    node_type: str  # source, process, output, usage
    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LineageEdge:
    """血缘边（关系）"""
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str  # produces, transforms, consumes
    description: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class DataLineageTracker:
    """数据血缘追踪器"""

    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: Dict[str, LineageEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}  # node_id -> [edge_ids]
        self._reverse_adj: Dict[str, List[str]] = {}  # node_id -> [incoming edge_ids]
        logger.info("DataLineageTracker initialized")

    def add_node(
        self,
        node_type: str,
        name: str,
        description: str,
        metadata: Dict[str, Any] = None,
        node_id: str = None
    ) -> LineageNode:
        """添加血缘节点"""
        if node_id is None:
            node_id = f"{node_type}_{uuid.uuid4().hex[:8]}"

        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            description=description,
            metadata=metadata or {}
        )
        self._nodes[node_id] = node
        self._adjacency.setdefault(node_id, [])
        self._reverse_adj.setdefault(node_id, [])
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        description: str
    ) -> LineageEdge:
        """添加血缘关系"""
        if source_id not in self._nodes:
            raise ValueError(f"源节点 {source_id} 不存在")
        if target_id not in self._nodes:
            raise ValueError(f"目标节点 {target_id} 不存在")

        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        edge = LineageEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            description=description
        )
        self._edges[edge_id] = edge
        self._adjacency.setdefault(source_id, []).append(edge_id)
        self._reverse_adj.setdefault(target_id, []).append(edge_id)
        return edge

    def trace_upstream(self, node_id: str, max_depth: int = 10) -> List[LineageNode]:
        """追溯上游数据来源（BFS）"""
        if node_id not in self._nodes:
            return []

        visited: Set[str] = set()
        result: List[LineageNode] = []
        queue = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            result.append(self._nodes[current_id])

            # 查找入边
            for edge_id in self._reverse_adj.get(current_id, []):
                edge = self._edges[edge_id]
                if edge.source_id not in visited:
                    queue.append((edge.source_id, depth + 1))

        return result

    def trace_downstream(self, node_id: str, max_depth: int = 10) -> List[LineageNode]:
        """追踪下游数据使用（BFS）"""
        if node_id not in self._nodes:
            return []

        visited: Set[str] = set()
        result: List[LineageNode] = []
        queue = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            result.append(self._nodes[current_id])

            # 查找出边
            for edge_id in self._adjacency.get(current_id, []):
                edge = self._edges[edge_id]
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

        return result

    def get_lineage_graph(
        self,
        center_node_id: str = None,
        depth: int = 3
    ) -> Dict[str, Any]:
        """获取血缘图数据（ECharts 格式）"""
        colors = {
            "source": "#5470c6",
            "process": "#91cc75",
            "output": "#fac858",
            "usage": "#ee6666"
        }
        cat_map = {"source": 0, "process": 1, "output": 2, "usage": 3}

        if center_node_id:
            upstream = {n.node_id for n in self.trace_upstream(center_node_id, depth)}
            downstream = {n.node_id for n in self.trace_downstream(center_node_id, depth)}
            all_ids = upstream | downstream
        else:
            all_ids = set(self._nodes.keys())

        # 构建 ECharts 节点
        nodes = []
        for nid in all_ids:
            node = self._nodes[nid]
            nodes.append({
                "id": node.node_id,
                "name": node.name,
                "category": cat_map.get(node.node_type, 0),
                "symbolSize": 50 if node.node_type == "source" else 35,
                "itemStyle": {"color": colors.get(node.node_type, "#666666")},
                "tooltip": {
                    "formatter": f"<b>{node.name}</b><br/>{node.description}<br/>类型: {node.node_type}"
                }
            })

        # 构建 ECharts 边
        edges = []
        for edge in self._edges.values():
            if edge.source_id in all_ids and edge.target_id in all_ids:
                edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "label": {
                        "show": True,
                        "formatter": edge.relation_type,
                        "fontSize": 10
                    },
                    "lineStyle": {
                        "curveness": 0.2,
                        "color": "#aaa"
                    }
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "categories": [
                {"name": "数据源", "itemStyle": {"color": colors["source"]}},
                {"name": "处理过程", "itemStyle": {"color": colors["process"]}},
                {"name": "输出", "itemStyle": {"color": colors["output"]}},
                {"name": "使用", "itemStyle": {"color": colors["usage"]}}
            ]
        }

    def record_data_flow(
        self,
        source_name: str,
        process_name: str,
        output_name: str,
        usage_name: str = None,
        source_metadata: Dict = None,
        process_metadata: Dict = None,
        output_metadata: Dict = None
    ) -> Dict[str, LineageNode]:
        """记录完整的数据流转过程"""
        source = self.add_node("source", source_name, f"数据源: {source_name}", source_metadata)
        process = self.add_node("process", process_name, f"处理: {process_name}", process_metadata)
        output = self.add_node("output", output_name, f"输出: {output_name}", output_metadata)

        self.add_edge(source.node_id, process.node_id, "produces", "数据输入")
        self.add_edge(process.node_id, output.node_id, "transforms", "数据处理")

        result = {"source": source, "process": process, "output": output}

        if usage_name:
            usage = self.add_node("usage", usage_name, f"使用: {usage_name}")
            self.add_edge(output.node_id, usage.node_id, "consumes", "数据消费")
            result["usage"] = usage

        return result

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """获取单个节点"""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[LineageNode]:
        """获取所有节点"""
        return list(self._nodes.values())

    def get_all_edges(self) -> List[LineageEdge]:
        """获取所有边"""
        return list(self._edges.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        for node in self._nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_type_counts": type_counts,
            "lineage_chain_hash": self._compute_chain_hash(),
        }

    def _compute_chain_hash(self) -> str:
        """计算血缘链的 SM3 哈希，用于区块链存证"""
        import json
        from app.services.gmssl_real import sm3_engine
        data = json.dumps(
            [n.to_dict() for n in self._nodes.values()] +
            [e.to_dict() for e in self._edges], sort_keys=True
        )
        return sm3_engine.hash(data.encode('utf-8'))

    def get_chain_hash(self) -> str:
        return self._compute_chain_hash()

    def clear(self):
        """清空所有数据"""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adj.clear()


# ============================================================
# 全局单例
# ============================================================
data_lineage_tracker = DataLineageTracker()
