"""L3 知识图谱模块

使用 KuzuDB 存储实体关系图谱，支持：
- 动态节点类型和关系类型
- 从 L1/L2 总结中自动提取实体
- LLM Tool 手动保存知识
- 路径扩展检索
- 容量管理和遗忘淘汰
"""

from .models import (
    GraphNode,
    GraphEdge,
    ExtractionResult,
    NODE_TYPE_WHITELIST,
    RELATION_TYPE_WHITELIST
)
from .adapter import L3KGAdapter
from .extractor import EntityExtractor
from .retriever import GraphRetriever
from .eviction import KGEvictionManager

__all__ = [
    # 数据模型
    "GraphNode",
    "GraphEdge",
    "ExtractionResult",
    "NODE_TYPE_WHITELIST",
    "RELATION_TYPE_WHITELIST",
    # 组件
    "L3KGAdapter",
    "EntityExtractor",
    "GraphRetriever",
    "KGEvictionManager",
]
