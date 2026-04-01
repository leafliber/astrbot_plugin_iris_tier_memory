"""
Iris Tier Memory - L1 消息缓冲组件

提供消息队列管理、自动总结触发等功能。
支持群聊隔离和人格切换时清空所有队列。
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from iris_memory.utils import count_tokens
from .models import ContextMessage, MessageQueue
from .summarizer import Summarizer

logger = get_logger("buffer")


# ============================================================================
# L1 缓冲组件
# ============================================================================

class L1Buffer(Component):
    """L1 消息缓冲组件
    
    管理消息队列，支持：
    - 按群聊隔离存储消息
    - 自动总结触发（阶段 5 后可用）
    - 清空单个队列或所有队列
    
    Attributes:
        _queues: 消息队列字典 {group_id: MessageQueue}
        _summarizer: 总结器实例（延迟初始化）
        _component_manager: 组件管理器引用（用于获取 LLMManager）
        _provider: 总结使用的 Provider ID
    
    Examples:
        >>> buffer = L1Buffer()
        >>> await buffer.initialize()
        >>> msg = ContextMessage(
        ...     role="user",
        ...     content="你好",
        ...     timestamp=datetime.now(),
        ...     token_count=2,
        ...     source="group_123"
        ... )
        >>> await buffer.add_message("group_123", msg)
        >>> context = buffer.get_context("group_123", 10)
        >>> len(context)
        1
    """
    
    def __init__(self):
        """初始化 L1 缓冲组件"""
        super().__init__()
        self._queues: Dict[str, MessageQueue] = {}
        self._summarizer: Optional[Summarizer] = None
        self._component_manager: Optional["ComponentManager"] = None
        self._provider: str = ""
        self._summarizing_locks: Dict[str, asyncio.Lock] = {}
        logger.debug("L1Buffer 实例已创建")
    
    @property
    def name(self) -> str:
        """组件名称
        
        Returns:
            组件名称 "l1_buffer"
        """
        return "l1_buffer"
    
    async def initialize(self) -> None:
        """初始化组件
        
        加载配置，总结器延迟创建（需要 LLMManager）。
        
        Raises:
            Exception: 初始化失败时抛出
        """
        try:
            config = get_config()
            
            # 检查是否启用
            if not config.get("l1_buffer.enable"):
                logger.info("L1 缓冲已禁用")
                self._is_available = False
                self._init_error = "L1 缓冲已禁用"
                return
            
            # 保存 Provider 配置，稍后创建总结器
            self._provider = config.get("l1_buffer.summary_provider")
            
            self._is_available = True
            logger.info("L1 缓冲组件初始化成功")
        
        except Exception as e:
            self._is_available = False
            self._init_error = str(e)
            logger.error(f"L1 缓冲组件初始化失败：{e}", exc_info=True)
            raise
    
    def set_component_manager(self, manager: "ComponentManager") -> None:
        """设置组件管理器引用
        
        用于延迟获取 LLMManager。
        
        Args:
            manager: 组件管理器实例
        """
        self._component_manager = manager
        logger.debug("L1Buffer 已获取 ComponentManager 引用")
    
    async def shutdown(self) -> None:
        """关闭组件
        
        清空所有队列，释放资源。
        """
        self.clear_all()
        self._is_available = False
        logger.info("L1 缓冲组件已关闭")
    
    def _get_or_create_summarizer(self) -> Optional[Summarizer]:
        """获取或创建 Summarizer（延迟初始化）
        
        Returns:
            Summarizer 实例，无法获取 LLMManager 时返回 None
        """
        # 如果已创建，直接返回
        if self._summarizer is not None:
            return self._summarizer
        
        # 检查 ComponentManager 是否可用
        if not self._component_manager:
            logger.warning("ComponentManager 未设置，无法创建 Summarizer")
            return None
        
        # 获取 LLMManager
        from iris_memory.llm import LLMManager
        llm_manager = self._component_manager.get_component("llm_manager")
        
        if not llm_manager or not llm_manager.is_available:
            logger.warning("LLMManager 不可用，无法创建 Summarizer")
            return None
        
        # 创建 Summarizer
        self._summarizer = Summarizer(
            llm_manager=llm_manager,
            provider=self._provider
        )
        logger.info("Summarizer 已延迟创建")
        
        return self._summarizer
    
    def _get_queue_key(self, group_id: str) -> str:
        """获取队列键
        
        根据群聊隔离配置决定队列键。
        
        Args:
            group_id: 群聊ID
        
        Returns:
            队列键（隔离模式下为 group_id，否则为 "default"）
        """
        config = get_config()
        
        if config.get("isolation_config.enable_group_memory_isolation"):
            return group_id
        else:
            return "default"
    
    def _get_or_create_queue(self, group_id: str) -> MessageQueue:
        """获取或创建队列
        
        如果队列不存在则创建。
        
        Args:
            group_id: 群聊ID
        
        Returns:
            消息队列实例
        """
        queue_key = self._get_queue_key(group_id)
        
        if queue_key not in self._queues:
            self._queues[queue_key] = MessageQueue(group_id=queue_key)
            logger.debug(f"创建新队列：{queue_key}")
        
        return self._queues[queue_key]
    
    async def add_message(
        self,
        group_id: str,
        role: str,
        content: str,
        source: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """添加消息到队列
        
        计算消息 Token 数，检查是否超限，添加到队列。
        触发自动总结检查。
        
        Args:
            group_id: 群聊ID
            role: 消息角色（user/assistant/system）
            content: 消息内容
            source: 消息来源（用户ID等）
            metadata: 额外元数据
        
        Returns:
            是否成功添加（超限消息返回 False）
        """
        if not self._is_available:
            logger.warning("L1 缓冲不可用，跳过消息添加")
            return False
        
        config = get_config()
        
        # 计算消息 Token 数
        token_count = count_tokens(content)
        
        # 检查单条消息 Token 数限制
        max_single_tokens = config.get("l1_buffer.max_single_message_tokens")
        if token_count > max_single_tokens:
            logger.warning(
                f"消息 Token 数 {token_count} 超过限制 {max_single_tokens}，已丢弃"
            )
            return False
        
        # 创建消息实例
        message = ContextMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            token_count=token_count,
            source=source,
            metadata=metadata or {}
        )
        
        # 获取或创建队列
        queue = self._get_or_create_queue(group_id)
        queue.add_message(message)
        
        logger.debug(
            f"消息已入队：{group_id}, role={role}, "
            f"tokens={token_count}, queue_size={len(queue)}"
        )
        
        # 检查是否触发总结
        await self._check_and_summarize(group_id)
        
        return True
    
    def get_context(
        self,
        group_id: str,
        max_length: Optional[int] = None
    ) -> list[ContextMessage]:
        """获取队列上下文
        
        返回指定群聊的消息列表，用于注入 LLM 请求。
        
        Args:
            group_id: 群聊ID
            max_length: 最大消息数（可选，默认使用配置）
        
        Returns:
            消息列表
        """
        if not self._is_available:
            logger.warning("L1 缓冲不可用，返回空上下文")
            return []
        
        config = get_config()
        queue_key = self._get_queue_key(group_id)
        
        if queue_key not in self._queues:
            return []
        
        queue = self._queues[queue_key]
        
        # 使用配置的最大长度
        if max_length is None:
            max_length = config.get("l1_buffer.inject_queue_length")
        
        # 返回最近的消息
        messages = list(queue.messages)
        if len(messages) > max_length:
            messages = messages[-max_length:]
        
        logger.debug(
            f"获取上下文：{group_id}, 返回 {len(messages)}/{len(queue)} 条消息"
        )
        
        return messages
    
    def clear_context(self, group_id: str) -> None:
        """清空指定群聊的队列
        
        Args:
            group_id: 群聊ID
        """
        queue_key = self._get_queue_key(group_id)
        
        if queue_key in self._queues:
            queue = self._queues[queue_key]
            old_size = len(queue)
            queue.clear()
            logger.info(f"已清空队列：{queue_key}，原 {old_size} 条消息")
    
    def clear_all(self) -> None:
        """清空所有队列
        
        用于人格切换时清空所有记忆。
        """
        total_messages = sum(len(q) for q in self._queues.values())
        self._queues.clear()
        logger.info(f"已清空所有队列，共 {total_messages} 条消息")
    
    async def _check_and_summarize(self, group_id: str) -> None:
        """检查并触发总结
        
        检查队列是否超过限制，触发自动总结。
        使用锁防止并发触发重复总结。
        
        阶段 2-4：总结功能不可用，仅清空队列
        阶段 5：调用 LLM 生成总结并写入 L2
        
        Args:
            group_id: 群聊ID
        """
        queue_key = self._get_queue_key(group_id)
        
        if queue_key not in self._summarizing_locks:
            self._summarizing_locks[queue_key] = asyncio.Lock()
        
        if self._summarizing_locks[queue_key].locked():
            logger.debug(f"群聊 {queue_key} 正在总结中，跳过重复触发")
            return
        
        async with self._summarizing_locks[queue_key]:
            summarizer = self._get_or_create_summarizer()
            
            if not summarizer:
                logger.debug("Summarizer 不可用，跳过总结检查")
                return
            
            if queue_key not in self._queues:
                return
            
            queue = self._queues[queue_key]
            
            if not summarizer.should_summarize(queue):
                return
            
            try:
                config = get_config()
                retain_count = config.get("l1_buffer.retain_message_count")
                max_queue_tokens = config.get("l1_buffer.max_queue_tokens")
                
                to_summarize, to_retain = queue.split_for_summary(
                    retain_count=retain_count,
                    max_retain_tokens=max_queue_tokens
                )
                
                if not to_summarize:
                    logger.debug(f"队列 {queue_key} 无需总结的消息")
                    return
                
                logger.info(
                    f"开始总结队列：{queue_key}，"
                    f"待总结 {len(to_summarize)} 条，保留 {len(to_retain)} 条"
                )
                
                summary = await summarizer.summarize(to_summarize)
                
                if summary:
                    logger.info(f"总结完成：{queue_key}, 长度：{len(summary)}")
                    
                    active_users = list(
                        set(msg.source for msg in to_summarize if msg.role == "user")
                    )
                    
                    memory_id = await self._write_summary_to_l2(
                        group_id, to_summarize, summary
                    )
                    
                    await self._extract_and_store_to_kg(
                        group_id, summary, memory_id, active_users
                    )
                    
                    await self._update_profile_after_summary(
                        group_id, to_summarize, summary
                    )
                else:
                    logger.warning(f"总结返回空，队列 {queue_key}")
                
                queue.remove_messages(to_summarize)
                logger.info(
                    f"队列已更新：{queue_key}，剩余 {len(queue)} 条消息，"
                    f"{queue.total_tokens} tokens"
                )
            
            except Exception as e:
                logger.error(
                    f"总结队列 {queue_key} 失败：{e}",
                    exc_info=True
                )
                queue.clear()
    
    async def _update_profile_after_summary(
        self,
        group_id: str,
        messages: list[ContextMessage],
        summary: str
    ) -> None:
        """总结后更新画像（内部函数）
        
        更新群聊画像的当前话题和活跃用户列表。
        
        Args:
            group_id: 群聊ID
            messages: 被总结的消息列表
            summary: 总结文本
        """
        config = get_config()
        if not config.get("profile.enable"):
            return
        
        if not self._component_manager:
            return
        
        profile_storage = self._component_manager.get_component("profile")
        if not profile_storage or not profile_storage.is_available:
            return
        
        try:
            from iris_memory.profile import GroupProfileManager
            
            group_manager = GroupProfileManager(profile_storage)
            
            active_users = list(
                set(msg.source for msg in messages if msg.role == "user")
            )
            
            current_topic = summary[:100] if len(summary) > 100 else summary
            
            await group_manager.update_simple_fields(
                group_id=group_id,
                current_topic=current_topic,
                active_users=active_users
            )
            
            logger.debug(f"总结后更新群聊画像: {group_id}")
        
        except Exception as e:
            logger.error(f"更新群聊画像失败: {e}", exc_info=True)
    
    async def _write_summary_to_l2(
        self,
        group_id: str,
        messages: list[ContextMessage],
        summary: str
    ) -> Optional[str]:
        """将总结写入 L2 记忆库
        
        Args:
            group_id: 群聊ID
            messages: 被总结的消息列表
            summary: 总结文本
        
        Returns:
            记忆 ID，失败时返回 None
        """
        config = get_config()
        if not config.get("l2_memory.enable"):
            logger.debug("L2 记忆库未启用，跳过写入")
            return None
        
        if not self._component_manager:
            return None
        
        l2_adapter = self._component_manager.get_component("l2_memory")
        if not l2_adapter or not l2_adapter.is_available:
            logger.debug("L2 记忆库组件不可用，跳过写入")
            return None
        
        try:
            from iris_memory.l2_memory import MemoryRetriever
            
            retriever = MemoryRetriever(self._component_manager)
            
            metadata = {
                "group_id": group_id,
                "source": "l1_summary",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.8,
            }
            
            active_users = list(
                set(msg.source for msg in messages if msg.role == "user")
            )
            if active_users:
                metadata["active_users"] = ",".join(active_users)
            
            # 写入记忆
            memory_id = await retriever.add_from_summary(summary, metadata)
            
            if memory_id:
                logger.info(f"已将总结写入 L2 记忆库：{memory_id}")
            else:
                logger.warning("写入 L2 记忆库失败")
            
            return memory_id
        
        except Exception as e:
            logger.error(f"写入 L2 记忆库失败: {e}", exc_info=True)
            return None
    
    async def _extract_and_store_to_kg(
        self,
        group_id: str,
        summary: str,
        memory_id: Optional[str],
        active_users: Optional[list[str]] = None
    ) -> None:
        """从总结中提取实体和关系，存储到知识图谱
        
        Args:
            group_id: 群聊ID
            summary: 总结文本
            memory_id: L2 记忆 ID（可选）
            active_users: 活跃用户ID列表（可选）
        """
        # 检查知识图谱是否启用
        config = get_config()
        if not config.get("l3_kg.enable"):
            logger.debug("L3 知识图谱未启用，跳过实体提取")
            return
        
        # 获取组件
        if not self._component_manager:
            return
        
        llm_manager = self._component_manager.get_component("llm_manager")
        if not llm_manager or not llm_manager.is_available:
            logger.debug("LLM Manager 不可用，跳过实体提取")
            return
        
        kg_adapter = self._component_manager.get_component("l3_kg")
        if not kg_adapter or not kg_adapter.is_available:
            logger.debug("L3 知识图谱组件不可用，跳过实体提取")
            return
        
        try:
            from iris_memory.l3_kg import EntityExtractor
            
            # 创建实体提取器
            extractor = EntityExtractor(llm_manager)
            
            # 构建上下文信息
            context = {
                "group_id": group_id,
                "source_memory_id": memory_id,
                "active_users": active_users or [],
            }
            
            # 提取实体和关系
            result = await extractor.extract_from_text(summary, context)
            
            if not result.nodes and not result.edges:
                logger.debug("未从总结中提取到实体或关系")
                return
            
            # 存储节点到图谱
            node_count = 0
            for node in result.nodes:
                success = await kg_adapter.add_node(node)
                if success:
                    node_count += 1
            
            # 存储边到图谱
            edge_count = 0
            for edge in result.edges:
                success = await kg_adapter.add_edge(edge)
                if success:
                    edge_count += 1
            
            logger.info(
                f"已将实体和关系存储到知识图谱："
                f"{node_count}/{len(result.nodes)} 个节点，"
                f"{edge_count}/{len(result.edges)} 条边"
            )
        
        except Exception as e:
            logger.error(f"提取实体和存储到图谱失败: {e}", exc_info=True)
    
    def get_queue_stats(self, group_id: str) -> Optional[Dict]:
        """获取队列统计信息
        
        Args:
            group_id: 群聊ID
        
        Returns:
            统计信息字典，队列不存在时返回 None
        """
        queue_key = self._get_queue_key(group_id)
        
        if queue_key not in self._queues:
            return None
        
        queue = self._queues[queue_key]
        
        return {
            "group_id": queue_key,
            "message_count": len(queue),
            "total_tokens": queue.total_tokens,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 L1 缓冲的全局统计信息
        
        Returns:
            统计信息字典
        """
        config = get_config()
        
        # 计算总消息数和总 Token 数
        total_messages = 0
        total_tokens = 0
        queue_count = len(self._queues)
        
        for queue in self._queues.values():
            total_messages += len(queue)
            total_tokens += queue.total_tokens
        
        return {
            "queue_count": queue_count,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "max_capacity": config.get("l1_buffer.max_capacity", 100),
        }
