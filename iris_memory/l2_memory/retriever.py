"""
Iris Tier Memory - L2 记忆检索器

提供记忆检索、写入和访问更新的高级接口。
"""

from typing import List, Optional, Dict, Any, cast

from iris_memory.core import get_logger, ComponentManager
from iris_memory.config import get_config
from .models import MemoryEntry, MemorySearchResult
from .adapter import L2MemoryAdapter

logger = get_logger("l2_memory.retriever")


class MemoryRetriever:
    """记忆检索器
    
    提供记忆的高级检索和管理接口。
    
    Features:
        - 记忆检索（支持群聊隔离）
        - 从总结写入记忆
        - 访问频率更新
        - 图增强检索（阶段 4 实现）
        - Token 预算控制（阶段 8 实现）
    
    Examples:
        >>> retriever = MemoryRetriever(component_manager)
        >>> results = await retriever.retrieve("喜欢吃什么", group_id="group_123")
    """
    
    def __init__(self, component_manager: ComponentManager):
        """初始化检索器
        
        Args:
            component_manager: 组件管理器实例
        """
        self._manager = component_manager
        self._adapter: Optional[L2MemoryAdapter] = None
    
    def _get_adapter(self) -> Optional[L2MemoryAdapter]:
        """获取 L2 适配器
        
        Returns:
            L2MemoryAdapter 实例，不可用时返回 None
        """
        if self._adapter is None:
            adapter = self._manager.get_component("l2_memory")
            if adapter and adapter.is_available:
                self._adapter = cast(L2MemoryAdapter, adapter)
        return self._adapter
    
    async def retrieve(
        self,
        query: str,
        group_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[MemorySearchResult]:
        """检索记忆
        
        根据查询文本检索相似记忆。
        
        Args:
            query: 查询文本
            group_id: 群聊 ID（可选，用于隔离检索）
            top_k: 返回数量，默认从配置读取
        
        Returns:
            检索结果列表
        
        Examples:
            >>> results = await retriever.retrieve("用户喜欢什么")
            >>> len(results)
            10
        """
        config = get_config()
        
        # 获取适配器
        adapter = self._get_adapter()
        if not adapter:
            logger.debug("L2 记忆库不可用，返回空结果")
            return []
        
        # 获取 top_k 配置
        if top_k is None:
            top_k = config.get("l2_memory.top_k")
        
        # 检查群聊隔离配置
        enable_group_isolation = config.get("isolation_config.enable_group_memory_isolation")
        if not enable_group_isolation:
            # 关闭群聊隔离，不传递 group_id
            group_id = None
        
        # 执行检索
        results = await adapter.retrieve(query, group_id, top_k)
        
        logger.debug(f"检索到 {len(results)} 条记忆")
        return results
    
    async def add_from_summary(
        self,
        summary_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """从总结写入记忆
        
        将总结内容添加到记忆库。
        
        Args:
            summary_content: 总结内容
            metadata: 元数据（group_id、user_id 等）
        
        Returns:
            记忆 ID，失败时返回 None
        
        Examples:
            >>> memory_id = await retriever.add_from_summary(
            ...     "用户今天提到了喜欢吃苹果",
            ...     metadata={"group_id": "group_123", "confidence": 0.9}
            ... )
        """
        adapter = self._get_adapter()
        if not adapter:
            logger.warning("L2 记忆库不可用，跳过写入记忆")
            return None
        
        memory_id = await adapter.add_memory(summary_content, metadata)
        
        if memory_id:
            logger.info(f"已从总结写入记忆：{memory_id}")
        else:
            logger.warning("从总结写入记忆失败")
        
        return memory_id
    
    async def update_access(self, memory_id: str) -> bool:
        """更新记忆的访问信息
        
        增加访问次数并更新最近访问时间。
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            是否更新成功
        """
        adapter = self._get_adapter()
        if not adapter:
            return False
        
        return await adapter.update_access(memory_id)
    
    async def retrieve_for_context(
        self,
        query: str,
        group_id: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        """检索记忆并格式化为上下文文本
        
        检索记忆并格式化为适用于 LLM 上下文的文本。
        支持 Token 预算控制（阶段 8 完善）。
        
        Args:
            query: 查询文本
            group_id: 群聊 ID
            max_tokens: 最大 Token 数
        
        Returns:
            格式化的上下文文本
        
        Examples:
            >>> context = await retriever.retrieve_for_context(
            ...     "用户喜欢吃什么",
            ...     group_id="group_123"
            ... )
            >>> print(context)
            相关记忆：
            1. 用户喜欢吃苹果
            2. 用户昨天吃了香蕉
        """
        # 检索记忆
        results = await self.retrieve(query, group_id)
        
        if not results:
            return ""
        
        # 格式化为上下文文本
        context_lines = ["相关记忆："]
        current_tokens = 0
        
        for i, result in enumerate(results, 1):
            # 简单估算 Token 数（实际应使用 token_counter）
            estimated_tokens = len(result.entry.content) // 2
            
            if current_tokens + estimated_tokens > max_tokens:
                break
            
            context_lines.append(f"{i}. {result.entry.content}")
            current_tokens += estimated_tokens
        
        return "\n".join(context_lines)
