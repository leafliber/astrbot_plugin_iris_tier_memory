"""
Iris Tier Memory - L1 消息缓冲组件

提供消息队列管理、自动总结触发等功能。
支持群聊隔离和人格切换时清空所有队列。
"""

from typing import Optional, Dict
from datetime import datetime

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
        
        阶段 2-4：总结功能不可用，仅清空队列
        阶段 5：调用 LLM 生成总结并写入 L2
        
        Args:
            group_id: 群聊ID
        """
        # 延迟获取 Summarizer
        summarizer = self._get_or_create_summarizer()
        
        if not summarizer:
            logger.debug("Summarizer 不可用，跳过总结检查")
            return
        
        queue_key = self._get_queue_key(group_id)
        
        if queue_key not in self._queues:
            return
        
        queue = self._queues[queue_key]
        
        # 检查是否需要总结
        if not summarizer.should_summarize(queue):
            return
        
        try:
            logger.info(f"开始总结队列：{queue_key}")
            
            # 调用总结器
            summary = await summarizer.summarize(queue)
            
            if summary:
                # 阶段 5：将总结写入 L2（阶段 3 实现）
                logger.info(f"总结完成：{queue_key}, 长度：{len(summary)}")
                
                # 阶段 9：更新群聊画像（总结后更新）
                await self._update_profile_after_summary(group_id, queue, summary)
            else:
                # 总结返回空
                logger.warning(
                    f"总结返回空，队列 {queue_key} 将被清空"
                )
            
            # 清空队列
            queue.clear()
            logger.info(f"队列已清空：{queue_key}")
        
        except Exception as e:
            logger.error(
                f"总结队列 {queue_key} 失败：{e}，将清空队列",
                exc_info=True
            )
            # 即使失败也清空队列，避免重复触发
            queue.clear()
    
    async def _update_profile_after_summary(
        self,
        group_id: str,
        queue: MessageQueue,
        summary: str
    ) -> None:
        """总结后更新画像（内部函数）
        
        更新群聊画像的当前话题和活跃用户列表。
        
        Args:
            group_id: 群聊ID
            queue: 消息队列
            summary: 总结文本
        """
        # 检查画像系统是否启用
        config = get_config()
        if not config.get("profile.enable"):
            return
        
        # 获取 ProfileStorage 组件
        if not self._component_manager:
            return
        
        profile_storage = self._component_manager.get_component("profile")
        if not profile_storage or not profile_storage.is_available:
            return
        
        try:
            from iris_memory.profile import GroupProfileManager
            
            # 获取群聊画像管理器
            group_manager = GroupProfileManager(profile_storage)
            
            # 提取活跃用户列表（从 queue 中）
            active_users = list(set(msg.source for msg in queue if msg.role == "user"))
            
            # 提取当前话题（使用总结的前 100 字符）
            current_topic = summary[:100] if len(summary) > 100 else summary
            
            # 更新群聊画像简单字段
            await group_manager.update_simple_fields(
                group_id=group_id,
                current_topic=current_topic,
                active_users=active_users
            )
            
            logger.debug(f"总结后更新群聊画像: {group_id}")
        
        except Exception as e:
            logger.error(f"更新群聊画像失败: {e}", exc_info=True)
    
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
