"""
Iris Tier Memory - 记忆增强模块

提供记忆检索增强功能，包括：
- Token 预算控制：根据 Token 预算控制注入记忆的数量
- 图增强检索：向量检索结果结合知识图谱关系进行扩展
- 重排序增强：使用 LLM 对检索结果进行重排序

Examples:
    >>> from iris_memory.enhancement import EnhancedMemoryRetriever
    >>> retriever = EnhancedMemoryRetriever(component_manager, llm_manager)
    >>> context = await retriever.retrieve_with_enhancement(
    ...     query="用户喜欢什么",
    ...     group_id="group_123"
    ... )
"""

from .budget_control import TokenBudgetController
from .graph_enhancement import GraphEnhancer
from .reranker import MemoryReranker
from .enhanced_retriever import EnhancedMemoryRetriever

__all__ = [
    "TokenBudgetController",
    "GraphEnhancer",
    "MemoryReranker",
    "EnhancedMemoryRetriever",
]
