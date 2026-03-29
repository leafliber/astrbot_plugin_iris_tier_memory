"""
Iris Tier Memory - 整合增强检索器

整合 L2 检索、图增强、重排序和 Token 预算控制，提供统一的增强检索接口。
"""

from typing import List, Optional, TYPE_CHECKING
from iris_memory.core import get_logger, ComponentManager
from iris_memory.config import get_config
from iris_memory.l2_memory.models import MemorySearchResult
from iris_memory.l2_memory.retriever import MemoryRetriever
from .budget_control import TokenBudgetController
from .graph_enhancement import GraphEnhancer
from .reranker import MemoryReranker

if TYPE_CHECKING:
    from iris_memory.llm.manager import LLMManager

logger = get_logger("enhancement.enhanced_retriever")


class EnhancedMemoryRetriever:
    """整合增强检索器
    
    整合 L2 检索、图增强、重排序和 Token 预算控制。
    
    Features:
        - 向量检索（L2）
        - 图增强检索（可选）
        - Token 预算控制
        - 重排序（可选）
        - 统一接口
    
    Workflow:
        L2 向量检索 → 图增强（可选） → Token 预算裁剪 → 重排序（可选） → 格式化输出
    
    Examples:
        >>> retriever = EnhancedMemoryRetriever(
        ...     component_manager=component_manager,
        ...     llm_manager=llm_manager
        ... )
        >>> context = await retriever.retrieve_with_enhancement(
        ...     query="用户喜欢什么",
        ...     group_id="group_123"
        ... )
    """
    
    def __init__(
        self,
        component_manager: ComponentManager,
        llm_manager: Optional["LLMManager"] = None
    ):
        """初始化增强检索器
        
        Args:
            component_manager: 组件管理器实例
            llm_manager: LLM 调用管理器实例（可选，用于重排序）
        """
        self._manager = component_manager
        self._llm_manager = llm_manager
        self._config = get_config()
        
        # 初始化子组件
        self._l2_retriever = MemoryRetriever(component_manager)
        self._budget_controller = TokenBudgetController()
        self._graph_enhancer = GraphEnhancer(component_manager)
        
        # 重排序器延迟初始化（需要 LLM Manager）
        self._reranker: Optional[MemoryReranker] = None
    
    def _get_reranker(self) -> Optional[MemoryReranker]:
        """获取重排序器
        
        Returns:
            MemoryReranker 实例，LLM Manager 不可用时返回 None
        """
        if self._reranker is None and self._llm_manager:
            if self._llm_manager.is_available:
                self._reranker = MemoryReranker(self._llm_manager)
        
        return self._reranker
    
    async def retrieve_with_enhancement(
        self,
        query: str,
        group_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        enable_graph: Optional[bool] = None,
        enable_rerank: Optional[bool] = None
    ) -> str:
        """执行增强检索并格式化为上下文文本
        
        执行完整的增强检索流程：
        1. L2 向量检索
        2. 图增强（可选）
        3. Token 预算裁剪
        4. 重排序（可选）
        5. 格式化输出
        
        Args:
            query: 查询文本
            group_id: 群聊 ID
            max_tokens: 最大 Token 预算（可选，默认从配置读取）
            enable_graph: 是否启用图增强（可选，默认从配置读取）
            enable_rerank: 是否启用重排序（可选，默认从配置读取）
        
        Returns:
            格式化的上下文文本
        
        Examples:
            >>> context = await retriever.retrieve_with_enhancement(
            ...     query="用户喜欢什么",
            ...     group_id="group_123"
            ... )
        """
        logger.info(f"开始增强检索：query={query}, group_id={group_id}")
        
        # 1. L2 向量检索
        memories = await self._l2_retriever.retrieve(query, group_id)
        
        if not memories:
            logger.debug("L2 检索未找到相关记忆")
            return ""
        
        logger.debug(f"L2 检索到 {len(memories)} 条记忆")
        
        # 2. 图增强（可选）
        enable_graph_flag = (
            enable_graph
            if enable_graph is not None
            else self._config.get("l2_memory.enable_graph_enhancement", False)
        )
        
        graph_context = ""
        if enable_graph_flag:
            memories, graph_context = await self._graph_enhancer.enhance(
                memories=memories,
                group_id=group_id,
                query=query
            )
        
        # 3. Token 预算裁剪
        budget = max_tokens or self._config.get("token_budget_max_tokens", 2000)
        memories, actual_tokens = self._budget_controller.trim_memories(
            memories=memories,
            max_tokens=budget
        )
        
        logger.debug(f"Token 预算裁剪后：{len(memories)} 条记忆，{actual_tokens} tokens")
        
        # 4. 重排序（可选）
        enable_rerank_flag = (
            enable_rerank
            if enable_rerank is not None
            else self._config.get("enhancement.enable_rerank", False)
        )
        
        if enable_rerank_flag:
            reranker = self._get_reranker()
            if reranker:
                memories = await reranker.rerank(
                    memories=memories,
                    query=query
                )
        
        # 5. 格式化输出
        context = self._format_context(memories, graph_context)
        
        logger.info(
            f"增强检索完成：{len(memories)} 条记忆，"
            f"{actual_tokens} tokens，"
            f"图增强={'启用' if enable_graph_flag else '禁用'}，"
            f"重排序={'启用' if enable_rerank_flag else '禁用'}"
        )
        
        return context
    
    async def retrieve_memories_only(
        self,
        query: str,
        group_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        enable_rerank: Optional[bool] = None
    ) -> List[MemorySearchResult]:
        """执行增强检索并返回记忆列表（不格式化）
        
        适用于需要进一步处理记忆的场景。
        
        Args:
            query: 查询文本
            group_id: 群聊 ID
            max_tokens: 最大 Token 预算（可选）
            enable_rerank: 是否启用重排序（可选）
        
        Returns:
            记忆检索结果列表
        
        Examples:
            >>> memories = await retriever.retrieve_memories_only(
            ...     query="用户喜欢什么",
            ...     group_id="group_123"
            ... )
        """
        # 1. L2 向量检索
        memories = await self._l2_retriever.retrieve(query, group_id)
        
        if not memories:
            return []
        
        # 2. Token 预算裁剪
        budget = max_tokens or self._config.get("token_budget_max_tokens", 2000)
        memories, _ = self._budget_controller.trim_memories(
            memories=memories,
            max_tokens=budget
        )
        
        # 3. 重排序（可选）
        enable_rerank_flag = (
            enable_rerank
            if enable_rerank is not None
            else self._config.get("enhancement.enable_rerank", False)
        )
        
        if enable_rerank_flag:
            reranker = self._get_reranker()
            if reranker:
                memories = await reranker.rerank(
                    memories=memories,
                    query=query
                )
        
        return memories
    
    def _format_context(
        self,
        memories: List[MemorySearchResult],
        graph_context: str
    ) -> str:
        """格式化记忆和图谱为上下文文本
        
        Args:
            memories: 记忆列表
            graph_context: 图谱上下文文本
        
        Returns:
            格式化的上下文文本
        """
        lines = []
        
        # 添加记忆部分
        if memories:
            lines.append("## 相关记忆")
            for i, memory in enumerate(memories, 1):
                content = memory.entry.content
                lines.append(f"{i}. {content}")
        
        # 添加图谱部分
        if graph_context:
            lines.append("\n" + graph_context)
        
        return "\n".join(lines) if lines else ""
