"""
Iris Tier Memory - L1 数据模型

定义 L1 消息上下文缓冲的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, Dict, Any
from collections import deque


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ContextMessage:
    """消息数据类
    
    存储单条消息的完整信息，包括角色、内容、时间戳、Token 数等。
    
    Attributes:
        role: 消息角色（user/assistant/system）
        content: 消息内容
        timestamp: 消息时间戳
        token_count: Token 数量
        source: 消息来源（群聊ID或用户ID）
        metadata: 额外元数据（如用户昵称、消息ID等）
    
    Examples:
        >>> msg = ContextMessage(
        ...     role="user",
        ...     content="你好",
        ...     timestamp=datetime.now(),
        ...     token_count=2,
        ...     source="group_123"
        ... )
        >>> msg.role
        'user'
    """
    
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    token_count: int
    source: str  # 群聊ID或用户ID
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        
        Examples:
            >>> msg = ContextMessage(
            ...     role="user",
            ...     content="你好",
            ...     timestamp=datetime(2024, 1, 1, 12, 0),
            ...     token_count=2,
            ...     source="group_123"
            ... )
            >>> d = msg.to_dict()
            >>> d["role"]
            'user'
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "token_count": self.token_count,
            "source": self.source,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextMessage":
        """从字典创建实例
        
        Args:
            data: 包含消息数据的字典
        
        Returns:
            ContextMessage 实例
        
        Examples:
            >>> data = {
            ...     "role": "user",
            ...     "content": "你好",
            ...     "timestamp": "2024-01-01T12:00:00",
            ...     "token_count": 2,
            ...     "source": "group_123"
            ... }
            >>> msg = ContextMessage.from_dict(data)
            >>> msg.role
            'user'
        """
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            token_count=data["token_count"],
            source=data["source"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class MessageQueue:
    """消息队列数据类
    
    管理单个群聊的消息队列，支持消息入队、出队、Token 统计。
    
    Attributes:
        group_id: 群聊ID（隔离模式下）或 "default"（全局模式）
        messages: 消息队列（使用 deque 实现 O(1) 操作）
        total_tokens: 队列总 Token 数
        max_length: 队列最大长度（可选）
        max_tokens: 队列最大 Token 数（可选）
    
    Examples:
        >>> queue = MessageQueue(group_id="group_123")
        >>> msg = ContextMessage(
        ...     role="user",
        ...     content="你好",
        ...     timestamp=datetime.now(),
        ...     token_count=2,
        ...     source="group_123"
        ... )
        >>> queue.add_message(msg)
        >>> queue.total_tokens
        2
    """
    
    group_id: str
    messages: deque[ContextMessage] = field(default_factory=deque)
    total_tokens: int = 0
    max_length: Optional[int] = None
    max_tokens: Optional[int] = None
    
    def add_message(self, message: ContextMessage) -> None:
        """添加消息到队列
        
        将消息添加到队列末尾，并更新总 Token 数。
        
        Args:
            message: 要添加的消息
        """
        self.messages.append(message)
        self.total_tokens += message.token_count
    
    def remove_oldest(self) -> Optional[ContextMessage]:
        """移除最旧的消息
        
        从队列头部移除最旧的消息，并更新总 Token 数。
        
        Returns:
            被移除的消息，队列为空时返回 None
        """
        if not self.messages:
            return None
        
        message = self.messages.popleft()
        self.total_tokens -= message.token_count
        return message
    
    def clear(self) -> None:
        """清空队列
        
        移除所有消息并重置 Token 计数。
        """
        self.messages.clear()
        self.total_tokens = 0
    
    def __len__(self) -> int:
        """获取队列长度
        
        Returns:
            队列中的消息数量
        """
        return len(self.messages)
    
    def is_empty(self) -> bool:
        """检查队列是否为空
        
        Returns:
            队列是否为空
        """
        return len(self.messages) == 0
    
    def to_message_list(self) -> list[Dict[str, str]]:
        """转换为 OpenAI Chat API 格式的消息列表
        
        返回适用于 LLM 调用的消息列表格式。
        
        Returns:
            消息列表，每条消息包含 role 和 content
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def split_for_summary(
        self, 
        retain_count: int,
        max_retain_tokens: Optional[int] = None
    ) -> tuple[list[ContextMessage], list[ContextMessage]]:
        """分割队列为待总结消息和保留消息
        
        保留最新的 retain_count 条消息，返回需要总结的旧消息。
        同时考虑 max_retain_tokens 限制，避免保留消息过长。
        
        Args:
            retain_count: 保留的消息数量
            max_retain_tokens: 保留消息的最大 Token 数（可选）
        
        Returns:
            (待总结的消息列表, 保留的消息列表)
        
        Examples:
            >>> queue = MessageQueue(group_id="test")
            >>> # 添加 20 条消息
            >>> for i in range(20):
            ...     queue.add_message(ContextMessage(...))
            >>> to_summarize, to_retain = queue.split_for_summary(retain_count=10)
            >>> len(to_summarize)
            10
            >>> len(to_retain)
            10
        """
        if len(self.messages) <= retain_count:
            return [], list(self.messages)
        
        messages_list = list(self.messages)
        to_retain = messages_list[-retain_count:]
        to_summarize = messages_list[:-retain_count]
        
        if max_retain_tokens is not None:
            retain_tokens = sum(msg.token_count for msg in to_retain)
            if retain_tokens > max_retain_tokens:
                while len(to_retain) > 1 and retain_tokens > max_retain_tokens:
                    moved_msg = to_retain.pop(0)
                    to_summarize.append(moved_msg)
                    retain_tokens -= moved_msg.token_count
        
        return to_summarize, to_retain
    
    def remove_messages(self, messages: list[ContextMessage]) -> None:
        """从队列中移除指定消息
        
        移除消息并更新 Token 计数。
        
        Args:
            messages: 要移除的消息列表
        """
        message_set = set(id(m) for m in messages)
        new_messages = deque()
        removed_tokens = 0
        
        for msg in self.messages:
            if id(msg) in message_set:
                removed_tokens += msg.token_count
            else:
                new_messages.append(msg)
        
        self.messages = new_messages
        self.total_tokens -= removed_tokens
