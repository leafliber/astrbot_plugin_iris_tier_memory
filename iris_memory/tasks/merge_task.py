"""
Iris Tier Memory - 记忆合并任务

定期检索相似记忆并使用 LLM 合并碎片化记忆。

Features:
    - 相似记忆检索
    - LLM 智能合并
    - 批量处理优化
    - 写锁保护
"""

from typing import TYPE_CHECKING, List, Optional, Tuple
from datetime import datetime

from iris_memory.core import get_logger
from iris_memory.config import get_config

if TYPE_CHECKING:
    from iris_memory.core import ComponentManager
    from iris_memory.llm import LLMManager
    from iris_memory.l2_memory import L2MemoryAdapter

logger = get_logger("tasks.merge")


class MergeTask:
    """记忆合并任务
    
    定期合并碎片化的相似记忆，提高记忆质量。
    
    Attributes:
        _component_manager: 组件管理器引用
        _similarity_threshold: 相似度阈值
        _batch_size: 批处理大小
    
    Examples:
        >>> task = MergeTask(component_manager)
        >>> await task.execute()
    """
    
    def __init__(self, component_manager: "ComponentManager"):
        """初始化记忆合并任务
        
        Args:
            component_manager: 组件管理器实例
        """
        self._component_manager = component_manager
        self._similarity_threshold = 0.85
        self._batch_size = 10
    
    async def execute(self) -> None:
        """执行记忆合并任务
        
        检索相似记忆并合并。
        """
        config = get_config()
        self._similarity_threshold = config.get("merge_similarity_threshold")
        self._batch_size = config.get("merge_batch_size")
        
        if not config.get("scheduled_tasks.enable_merging"):
            logger.debug("记忆合并任务未启用，跳过")
            return
        
        await self._merge_similar_memories()
    
    # =========================================================================
    # 记忆合并
    # =========================================================================
    
    async def _merge_similar_memories(self) -> None:
        """检索并合并相似记忆
        
        流程：
        1. 获取所有记忆
        2. 找出相似记忆对
        3. 使用 LLM 合并
        4. 更新存储
        """
        from iris_memory.l2_memory import L2MemoryAdapter
        
        # 获取 L2 适配器
        l2_adapter = self._component_manager.get_component("l2_memory")
        if not l2_adapter or not l2_adapter.is_available:
            logger.debug("L2 记忆库不可用，跳过合并")
            return
        
        l2_adapter = l2_adapter  # type: L2MemoryAdapter
        
        # 获取 LLM 管理器
        llm_manager = self._component_manager.get_component("llm_manager")
        if not llm_manager or not llm_manager.is_available:
            logger.warning("LLMManager 不可用，无法合并记忆")
            return
        
        llm_manager = llm_manager  # type: LLMManager
        
        try:
            # 获取所有记忆
            entries = await l2_adapter.get_all_entries()
            
            if len(entries) < 2:
                logger.debug("记忆数量不足，无需合并")
                return
            
            logger.info(f"开始分析 {len(entries)} 条记忆的相似度...")
            
            # 找出相似记忆对
            similar_pairs = await self._find_similar_pairs(entries, l2_adapter)
            
            if not similar_pairs:
                logger.debug("未发现相似记忆，无需合并")
                return
            
            logger.info(f"发现 {len(similar_pairs)} 对相似记忆")
            
            # 合并记忆对
            merged_count = 0
            for mem1, mem2 in similar_pairs[:self._batch_size]:
                try:
                    # 合并记忆
                    merged_content = await self._merge_memories(
                        mem1.content,
                        mem2.content,
                        llm_manager
                    )
                    
                    if merged_content:
                        # 创建合并后的新记忆
                        await l2_adapter.add_memory(
                            merged_content,
                            metadata={
                                "group_id": mem1.metadata.get("group_id"),
                                "confidence": max(
                                    mem1.metadata.get("confidence", 0.5),
                                    mem2.metadata.get("confidence", 0.5)
                                ),
                                "timestamp": datetime.now().isoformat(),
                                "merged_from": f"{mem1.id},{mem2.id}"
                            }
                        )
                        
                        # 删除旧记忆
                        await l2_adapter.delete_entries([mem1.id, mem2.id])
                        
                        merged_count += 1
                        logger.debug(f"已合并记忆：{mem1.id} + {mem2.id}")
                
                except Exception as e:
                    logger.error(f"合并记忆失败：{e}", exc_info=True)
            
            logger.info(f"记忆合并完成，共合并 {merged_count} 对记忆")
            
        except Exception as e:
            logger.error(f"记忆合并任务失败：{e}", exc_info=True)
    
    async def _find_similar_pairs(
        self,
        entries: List,
        adapter: "L2MemoryAdapter"
    ) -> List[Tuple]:
        """找出相似记忆对
        
        Args:
            entries: 所有记忆条目
            adapter: L2 适配器
        
        Returns:
            相似记忆对列表 [(mem1, mem2), ...]
        """
        similar_pairs = []
        
        # 遍历所有记忆对
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                mem1 = entries[i]
                mem2 = entries[j]
                
                # 跳过不同群聊的记忆（如果启用群聊隔离）
                config = get_config()
                if config.get("isolation_config.enable_group_memory_isolation"):
                    if mem1.metadata.get("group_id") != mem2.metadata.get("group_id"):
                        continue
                
                # 检查相似度
                # 注意：这里使用 ChromaDB 的检索功能来判断相似度
                # 由于 ChromaDB 已经在存储时计算了向量，我们可以直接检索
                try:
                    results = await adapter.retrieve(
                        query=mem1.content,
                        group_id=mem1.metadata.get("group_id"),
                        top_k=2  # 获取最相似的 2 条（包含自己）
                    )
                    
                    # 检查第二条结果是否是 mem2
                    if len(results) >= 2:
                        second_result = results[1]
                        
                        # 如果第二条是 mem2 且相似度足够高
                        if (second_result.entry.id == mem2.id and
                            second_result.score >= self._similarity_threshold):
                            similar_pairs.append((mem1, mem2))
                
                except Exception as e:
                    logger.warning(f"检查记忆相似度失败：{e}")
        
        return similar_pairs
    
    async def _merge_memories(
        self,
        content1: str,
        content2: str,
        llm_manager: "LLMManager"
    ) -> Optional[str]:
        """使用 LLM 合并两条记忆
        
        Args:
            content1: 第一条记忆内容
            content2: 第二条记忆内容
            llm_manager: LLM 管理器
        
        Returns:
            合并后的记忆内容，失败时返回 None
        """
        try:
            # 构建合并 prompt
            prompt = f"""请将以下两条相似的记忆合并为一条更完整、更准确的记忆。

记忆1：{content1}

记忆2：{content2}

要求：
1. 合并重复信息
2. 保留所有独特细节
3. 保持简洁清晰
4. 仅输出合并后的记忆内容，不要添加额外说明

合并后的记忆："""

            # 调用 LLM
            merged = await llm_manager.generate(
                prompt=prompt,
                module="scheduled_tasks"
            )
            
            return merged.strip() if merged else None
            
        except Exception as e:
            logger.error(f"LLM 合并记忆失败：{e}")
            return None
