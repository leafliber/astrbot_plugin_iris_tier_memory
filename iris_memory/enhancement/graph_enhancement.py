"""
Iris Tier Memory - 图增强检索器

向量检索结果结合知识图谱关系进行扩展。
"""

from typing import List, Optional, Tuple, cast
from iris_memory.core import get_logger, ComponentManager
from iris_memory.config import get_config
from iris_memory.l2_memory.models import MemorySearchResult
from iris_memory.l3_kg.retriever import GraphRetriever
from iris_memory.l3_kg.adapter import L3KGAdapter

logger = get_logger("enhancement.graph_enhancement")


class GraphEnhancer:
    """图增强检索器
    
    向量检索结果结合知识图谱关系进行扩展。
    
    Features:
        - 从 L2 记忆中提取节点 ID
        - 调用 L3 图谱进行路径扩展
        - 合并向量检索和图谱检索结果
    
    Examples:
        >>> enhancer = GraphEnhancer(component_manager)
        >>> enhanced_results, graph_context = await enhancer.enhance(
        ...     memories=vector_results,
        ...     group_id="group_123"
        ... )
    """
    
    def __init__(self, component_manager: ComponentManager):
        """初始化图增强检索器
        
        Args:
            component_manager: 组件管理器实例
        """
        self._manager = component_manager
        self._l3_retriever: Optional[GraphRetriever] = None
        self._config = get_config()
    
    def _get_l3_retriever(self) -> Optional[GraphRetriever]:
        """获取 L3 图谱检索器
        
        Returns:
            GraphRetriever 实例，不可用时返回 None
        """
        if self._l3_retriever is None:
            adapter = self._manager.get_component("l3_kg")
            if adapter and adapter.is_available:
                adapter = cast(L3KGAdapter, adapter)
                self._l3_retriever = GraphRetriever(adapter)
        
        return self._l3_retriever
    
    async def enhance(
        self,
        memories: List[MemorySearchResult],
        group_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> Tuple[List[MemorySearchResult], str]:
        """对向量检索结果进行图增强
        
        从 L2 记忆中提取节点 ID，调用 L3 图谱进行路径扩展，
        并返回增强后的记忆列表和图谱上下文文本。
        
        Args:
            memories: L2 向量检索结果
            group_id: 群聊 ID（用于图谱检索隔离）
            query: 原始查询文本（暂未使用）
        
        Returns:
            (增强后的记忆列表, 图谱上下文文本)
        
        Examples:
            >>> enhancer = GraphEnhancer(component_manager)
            >>> enhanced, graph_text = await enhancer.enhance(
            ...     memories=vector_results,
            ...     group_id="group_123"
            ... )
        """
        if not memories:
            return [], ""
        
        # 检查是否启用图增强
        enable_graph = self._config.get("l2_memory.enable_graph_enhancement", False)
        if not enable_graph:
            logger.debug("图增强未启用，跳过")
            return memories, ""
        
        # 获取 L3 检索器
        retriever = self._get_l3_retriever()
        if not retriever:
            logger.debug("L3 图谱不可用，跳过图增强")
            return memories, ""
        
        # 从 L2 记忆中提取节点 ID
        node_ids = self._extract_node_ids(memories)
        
        if not node_ids:
            logger.debug("L2 记忆中未找到关联的图谱节点，跳过图增强")
            return memories, ""
        
        # 执行图谱路径扩展
        try:
            nodes, edges = await retriever.retrieve_with_expansion(
                memory_node_ids=node_ids,
                group_id=group_id
            )
            
            if not nodes:
                logger.debug("图谱路径扩展未找到相关节点")
                return memories, ""
            
            # 格式化图谱结果为上下文文本
            graph_context = retriever.format_for_context(nodes, edges)
            
            logger.info(
                f"图增强完成：提取 {len(node_ids)} 个节点 ID，"
                f"扩展出 {len(nodes)} 个节点、{len(edges)} 条边"
            )
            
            # 更新节点访问计数
            all_node_ids = [node.get("id") for node in nodes if node.get("id")]
            if all_node_ids:
                await retriever.update_access_count(all_node_ids)
            
            return memories, graph_context
        
        except Exception as e:
            logger.error(f"图增强失败：{e}", exc_info=True)
            return memories, ""
    
    def _extract_node_ids(self, memories: List[MemorySearchResult]) -> List[str]:
        """从 L2 记忆中提取关联的图谱节点 ID
        
        节点 ID 可能存储在记忆的 metadata 中。
        
        Args:
            memories: L2 记忆检索结果
        
        Returns:
            节点 ID 列表
        
        Examples:
            >>> node_ids = enhancer._extract_node_ids(memories)
            >>> print(node_ids)  # ["node_001", "node_002"]
        """
        node_ids: List[str] = []
        
        for memory in memories:
            # 尝试从 metadata 中提取节点 ID
            metadata = memory.entry.metadata
            
            # 可能的字段名：kg_node_id, node_id, entity_id
            node_id = (
                metadata.get("kg_node_id") or
                metadata.get("node_id") or
                metadata.get("entity_id")
            )
            
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
        
        logger.debug(f"从 {len(memories)} 条记忆中提取 {len(node_ids)} 个节点 ID")
        return node_ids
