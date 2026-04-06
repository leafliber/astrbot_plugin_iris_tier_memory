"""
Iris Tier Memory - L3 知识图谱提取任务

定期检测未处理的 L2 记忆，当数量达到阈值时触发实体提取，
将实体和关系写入 L3 知识图谱。

Features:
    - 阈值触发机制
    - 相关记忆检索
    - 批量处理优化
    - 写锁保护
"""

from typing import TYPE_CHECKING, List

from iris_memory.core import get_logger
from iris_memory.config import get_config

if TYPE_CHECKING:
    from iris_memory.core import ComponentManager
    from iris_memory.llm import LLMManager
    from iris_memory.l2_memory import L2MemoryAdapter
    from iris_memory.l3_kg import L3KGAdapter

logger = get_logger("tasks.kg_extraction")


class KGExtractionTask:
    """L3 知识图谱提取任务
    
    定期检测未处理的 L2 记忆数量，达到阈值时执行实体提取。
    
    流程：
    1. 检测未处理记忆数量
    2. 数量 >= 阈值时执行提取
    3. 为每条记忆检索相关记忆
    4. 合并后提取实体和关系
    5. 写入 L3 知识图谱
    6. 标记记忆为已处理
    
    Attributes:
        _component_manager: 组件管理器引用
    """
    
    def __init__(self, component_manager: "ComponentManager"):
        """初始化提取任务
        
        Args:
            component_manager: 组件管理器实例
        """
        self._component_manager = component_manager
    
    async def execute(self) -> None:
        """执行提取任务
        
        检测未处理记忆数量，达到阈值时执行提取。
        """
        config = get_config()
        
        l3_kg_enable = config.get("l3_kg.enable")
        if not l3_kg_enable:
            logger.debug("L3 知识图谱未启用，跳过提取任务")
            return
        
        l2_adapter = self._get_l2_adapter()
        if not l2_adapter:
            logger.debug("L2 记忆库不可用，跳过提取任务")
            return
        
        kg_adapter = self._get_kg_adapter()
        if not kg_adapter:
            logger.debug("L3 知识图谱不可用，跳过提取任务")
            return
        
        llm_manager = self._get_llm_manager()
        if not llm_manager:
            logger.debug("LLM Manager 不可用，跳过提取任务")
            return
        
        min_unprocessed = config.get("kg_extraction_min_unprocessed")
        unprocessed_count = await l2_adapter.get_unprocessed_count()
        
        if unprocessed_count < min_unprocessed:
            logger.debug(
                f"未处理记忆数量 {unprocessed_count} < {min_unprocessed}，跳过提取"
            )
            return
        
        logger.info(f"开始 L3 知识图谱提取，未处理记忆数：{unprocessed_count}")
        
        batch_size = config.get("kg_extraction_batch_size")
        max_related = config.get("kg_extraction_max_related")
        
        unprocessed_memories = await l2_adapter.get_unprocessed_memories(limit=batch_size)
        
        if not unprocessed_memories:
            logger.debug("没有未处理的记忆")
            return
        
        from iris_memory.l3_kg import EntityExtractor, RelatedMemoryRetriever
        
        extractor = EntityExtractor(llm_manager)
        related_retriever = RelatedMemoryRetriever(self._component_manager)
        
        processed_ids: List[str] = []
        
        for memory in unprocessed_memories:
            try:
                related_memories = await related_retriever.retrieve_related(
                    memory, 
                    top_k=max_related
                )
                
                all_memories = [memory] + related_memories
                
                result = await extractor.extract_from_memories(all_memories)
                
                if result.nodes or result.edges:
                    node_count = 0
                    for node in result.nodes:
                        success = await kg_adapter.add_node(node)
                        if success:
                            node_count += 1
                    
                    edge_count = 0
                    for edge in result.edges:
                        success = await kg_adapter.add_edge(edge)
                        if success:
                            edge_count += 1
                    
                    logger.info(
                        f"记忆 {memory.id} 提取完成："
                        f"{node_count}/{len(result.nodes)} 个节点，"
                        f"{edge_count}/{len(result.edges)} 条边"
                    )
                
                processed_ids.append(memory.id)
                
            except Exception as e:
                logger.error(f"处理记忆 {memory.id} 失败：{e}", exc_info=True)
        
        if processed_ids:
            await l2_adapter.mark_memories_processed(processed_ids)
            logger.info(f"L3 提取任务完成，已处理 {len(processed_ids)} 条记忆")
    
    def _get_l2_adapter(self) -> "L2MemoryAdapter":
        """获取 L2 记忆适配器"""
        adapter = self._component_manager.get_component("l2_memory")
        if adapter and adapter.is_available:
            return adapter
        return None
    
    def _get_kg_adapter(self) -> "L3KGAdapter":
        """获取 L3 知识图谱适配器"""
        adapter = self._component_manager.get_component("l3_kg")
        if adapter and adapter.is_available:
            return adapter
        return None
    
    def _get_llm_manager(self) -> "LLMManager":
        """获取 LLM 管理器"""
        manager = self._component_manager.get_component("llm_manager")
        if manager and manager.is_available:
            return manager
        return None
