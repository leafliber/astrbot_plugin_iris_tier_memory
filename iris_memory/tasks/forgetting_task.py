"""
Iris Tier Memory - 遗忘清洗任务

定期计算记忆权重评分，批量清理评分低于阈值且超过保留期的条目。

Features:
    - L2 记忆库遗忘清洗
    - L3 知识图谱节点淘汰
    - 批量处理优化
    - 写锁保护
"""

from typing import TYPE_CHECKING, List, Optional
from datetime import datetime, timedelta

from iris_memory.core import get_logger
from iris_memory.config import get_config
from iris_memory.utils.forgetting import calculate_forgetting_score, should_evict

if TYPE_CHECKING:
    from iris_memory.core import ComponentManager
    from iris_memory.llm import LLMManager

logger = get_logger("tasks.forgetting")


class ForgettingTask:
    """遗忘清洗任务
    
    定期执行遗忘清洗，清理过期和低质量记忆。
    
    Attributes:
        _component_manager: 组件管理器引用
        _batch_size: 批处理大小
    
    Examples:
        >>> task = ForgettingTask(component_manager)
        >>> await task.execute()
    """
    
    def __init__(self, component_manager: "ComponentManager"):
        """初始化遗忘清洗任务
        
        Args:
            component_manager: 组件管理器实例
        """
        self._component_manager = component_manager
        self._batch_size = 100
    
    async def execute(self) -> None:
        """执行遗忘清洗任务
        
        依次执行 L2 和 L3 的遗忘清洗。
        """
        config = get_config()
        self._batch_size = config.get("eviction_batch_size")
        
        if not config.get("scheduled_tasks.enable_forgetting"):
            logger.debug("遗忘清洗任务未启用，跳过")
            return
        
        await self._evict_l2_memories()
        await self._merge_l3_duplicates()
        await self._evict_l3_nodes()
    
    # =========================================================================
    # L2 遗忘清洗
    # =========================================================================
    
    async def _evict_l2_memories(self) -> None:
        """L2 记忆库遗忘清洗
        
        获取所有记忆，计算遗忘评分，淘汰低分记忆。
        """
        from iris_memory.l2_memory import L2MemoryAdapter
        
        # 获取 L2 适配器
        l2_adapter = self._component_manager.get_component("l2_memory")
        if not l2_adapter or not l2_adapter.is_available:
            logger.debug("L2 记忆库不可用，跳过遗忘清洗")
            return
        
        l2_adapter = l2_adapter  # type: L2MemoryAdapter
        
        try:
            # 获取所有记忆条目
            entries = await l2_adapter.get_all_entries()
            
            if not entries:
                logger.debug("L2 记忆库为空，无需清洗")
                return
            
            logger.info(f"开始评估 {len(entries)} 条 L2 记忆...")
            
            # 计算遗忘评分并筛选待淘汰记忆
            to_evict = []
            config = get_config()
            
            for entry in entries:
                # 检查是否应该淘汰
                if should_evict(entry):
                    to_evict.append(entry.id)
                    
                    # 达到批处理大小时执行删除
                    if len(to_evict) >= self._batch_size:
                        await l2_adapter.evict_memories(to_evict)
                        to_evict = []
            
            # 删除剩余的记忆
            if to_evict:
                await l2_adapter.evict_memories(to_evict)
            
            logger.info(f"L2 遗忘清洗完成，共淘汰 {len(to_evict)} 条记忆")
            
        except Exception as e:
            logger.error(f"L2 遗忘清洗失败：{e}", exc_info=True)
    
    # =========================================================================
    # L3 图谱去重合并
    # =========================================================================
    
    async def _merge_l3_duplicates(self) -> None:
        """L3 知识图谱重复节点合并
        
        查找同名同 label 的重复节点并合并。
        """
        from iris_memory.l3_kg import L3KGAdapter
        
        l3_adapter = self._component_manager.get_component("l3_kg")
        if not l3_adapter or not l3_adapter.is_available:
            logger.debug("L3 知识图谱不可用，跳过去重合并")
            return
        
        l3_adapter = l3_adapter  # type: L3KGAdapter
        
        try:
            merged, deleted = await l3_adapter.merge_duplicate_nodes()
            if merged > 0:
                logger.info(f"L3 去重合并完成：合并 {merged} 组，删除 {deleted} 个重复节点")
        except Exception as e:
            logger.error(f"L3 去重合并失败：{e}", exc_info=True)
    
    # =========================================================================
    # L3 图谱淘汰
    # =========================================================================
    
    async def _evict_l3_nodes(self) -> None:
        """L3 知识图谱节点淘汰
        
        获取所有节点，计算遗忘评分，淘汰低分节点及关联边。
        """
        from iris_memory.l3_kg import L3KGAdapter
        from iris_memory.l3_kg.models import GraphNode
        
        # 获取 L3 适配器
        l3_adapter = self._component_manager.get_component("l3_kg")
        if not l3_adapter or not l3_adapter.is_available:
            logger.debug("L3 知识图谱不可用，跳过淘汰")
            return
        
        l3_adapter = l3_adapter  # type: L3KGAdapter
        
        try:
            # 获取所有节点
            nodes = await l3_adapter.get_all_nodes()
            
            if not nodes:
                logger.debug("L3 知识图谱为空，无需淘汰")
                return
            
            logger.info(f"开始评估 {len(nodes)} 个 L3 节点...")
            
            # 计算遗忘评分并筛选待淘汰节点
            to_evict = []
            config = get_config()
            
            # 获取 L3 遗忘配置
            threshold_kg = config.get("forgetting_threshold_kg")
            retention_days = config.get("kg_retention_days")
            
            for node_dict in nodes:
                # 转换为 GraphNode 对象（用于计算评分）
                node = GraphNode(
                    id=node_dict["id"],
                    label=node_dict["label"],
                    name=node_dict["name"],
                    content=node_dict["content"],
                    confidence=node_dict["confidence"],
                    access_count=node_dict["access_count"],
                    last_access_time=node_dict["last_access_time"],
                    created_time=node_dict["created_time"],
                    source_memory_id=node_dict["source_memory_id"],
                    group_id=node_dict["group_id"],
                    properties=node_dict["properties"]
                )
                
                # 检查是否应该淘汰
                if self._should_evict_node(node, threshold_kg, retention_days):
                    to_evict.append(node.id)
                    
                    # 达到批处理大小时执行删除
                    if len(to_evict) >= self._batch_size:
                        await l3_adapter.evict_nodes(to_evict)
                        to_evict = []
            
            # 删除剩余的节点
            if to_evict:
                await l3_adapter.evict_nodes(to_evict)
            
            logger.info(f"L3 图谱淘汰完成，共淘汰 {len(to_evict)} 个节点")
            
        except Exception as e:
            logger.error(f"L3 图谱淘汰失败：{e}", exc_info=True)
    
    def _should_evict_node(
        self,
        node,
        threshold: float,
        retention_days: int
    ) -> bool:
        """判断节点是否应该被淘汰
        
        Args:
            node: 图谱节点
            threshold: 遗忘阈值
            retention_days: 保留天数
        
        Returns:
            是否应该淘汰
        """
        # 计算遗忘评分
        # 注意：这里需要将 GraphNode 转换为类似 MemoryEntry 的结构
        # 因为 calculate_forgetting_score 接受 MemoryEntry
        
        from iris_memory.l2_memory.models import MemoryEntry
        
        # 创建临时 MemoryEntry 用于计算评分
        temp_entry = MemoryEntry(
            id=node.id,
            content=node.content,
            metadata={
                "last_access_time": node.last_access_time.isoformat() if node.last_access_time else None,
                "access_count": node.access_count,
                "confidence": node.confidence
            }
        )
        
        # 计算评分
        score = calculate_forgetting_score(temp_entry)
        
        if score < threshold:
            # 检查保留期
            last_access = node.last_access_time
            if last_access:
                days_elapsed = (datetime.now() - last_access).days
                if days_elapsed > retention_days:
                    return True
            else:
                # 无访问记录，根据评分决定
                return True
        
        return False
