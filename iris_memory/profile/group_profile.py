"""
Iris Tier Memory - 群聊画像管理器

封装群聊画像的业务逻辑。
"""

from typing import List, Optional
from datetime import datetime

from iris_memory.core import get_logger
from .storage import ProfileStorage
from .models import GroupProfile

logger = get_logger("profile")


# ============================================================================
# 群聊画像管理器
# ============================================================================

class GroupProfileManager:
    """群聊画像管理器
    
    封装群聊画像的业务逻辑，提供：
    - 获取/创建画像
    - 更新简单字段（实时）
    - 更新复杂字段（定时分析）
    
    Attributes:
        _storage: 画像存储组件实例
    
    Examples:
        >>> storage = ProfileStorage(context)
        >>> manager = GroupProfileManager(storage)
        >>> profile = await manager.get_or_create("group_123")
        >>> await manager.update_simple_fields("group_123", current_topic="AI技术")
    """
    
    def __init__(self, storage: ProfileStorage):
        """初始化群聊画像管理器
        
        Args:
            storage: 画像存储组件实例
        """
        self._storage = storage
    
    async def get_or_create(self, group_id: str) -> GroupProfile:
        """获取或创建群聊画像
        
        如果画像不存在，创建一个新的空画像。
        
        Args:
            group_id: 群聊ID
        
        Returns:
            群聊画像对象
        
        Examples:
            >>> profile = await manager.get_or_create("group_123")
            >>> profile.group_id
            'group_123'
        """
        profile = await self._storage.get_group_profile(group_id)
        
        if not profile:
            profile = GroupProfile(group_id=group_id)
            logger.info(f"创建新群聊画像: {group_id}")
        
        return profile
    
    async def update_simple_fields(
        self,
        group_id: str,
        current_topic: Optional[str] = None,
        active_users: Optional[List[str]] = None,
        group_name: Optional[str] = None
    ) -> None:
        """更新简单字段（实时记录）
        
        简单字段包括：当前话题、活跃用户列表、最近互动时间、群聊名称。
        这些字段在总结完成后直接更新，无需 LLM 调用。
        
        Args:
            group_id: 群聊ID
            current_topic: 当前话题（可选）
            active_users: 活跃用户列表（可选）
            group_name: 群聊名称（可选）
        
        Examples:
            >>> await manager.update_simple_fields(
            ...     "group_123",
            ...     current_topic="AI技术讨论",
            ...     active_users=["user1", "user2"]
            ... )
        """
        profile = await self.get_or_create(group_id)
        
        # 更新简单字段
        if current_topic is not None:
            profile.current_topic = current_topic
        
        if active_users is not None:
            profile.active_users = active_users
        
        if group_name is not None:
            profile.group_name = group_name
        
        # 更新最近互动时间
        profile.last_interaction_time = datetime.now()
        
        # 保存画像
        await self._storage.save_group_profile(profile)
        logger.debug(f"更新群聊画像简单字段: {group_id}")
    
    async def update_from_analysis(
        self,
        group_id: str,
        interests: List[str],
        atmosphere_tags: List[str],
        common_expressions: List[str],
        active_time_slots: Optional[List[str]] = None
    ) -> None:
        """从分析结果更新复杂字段（定时任务调用）
        
        复杂字段包括：群聊兴趣点、氛围标签、常用语/梗、活跃时段。
        这些字段通过 LLM 分析对话内容提取，由定时任务调用。
        
        Args:
            group_id: 群聊ID
            interests: 群聊兴趣点列表
            atmosphere_tags: 氛围标签列表
            common_expressions: 常用语/梗列表
            active_time_slots: 活跃时段列表（可选）
        
        Examples:
            >>> await manager.update_from_analysis(
            ...     "group_123",
            ...     interests=["技术", "AI"],
            ...     atmosphere_tags=["轻松", "技术范"],
            ...     common_expressions=["yyds", "绝了"]
            ... )
        """
        profile = await self.get_or_create(group_id)
        
        # 更新复杂字段
        profile.interests = interests
        profile.atmosphere_tags = atmosphere_tags
        profile.common_expressions = common_expressions
        
        if active_time_slots is not None:
            profile.active_time_slots = active_time_slots
        
        # 保存画像
        await self._storage.save_group_profile(profile)
        logger.info(f"从分析结果更新群聊画像: {group_id}")
    
    async def add_long_term_tag(
        self,
        group_id: str,
        tag: str
    ) -> None:
        """添加长期标签（人工或高质量LLM更新）
        
        长期标签描述群聊的核心特征，通常由人工设置或高质量 LLM 分析添加。
        
        Args:
            group_id: 群聊ID
            tag: 标签内容
        
        Examples:
            >>> await manager.add_long_term_tag("group_123", "技术交流群")
        """
        profile = await self.get_or_create(group_id)
        
        if tag not in profile.long_term_tags:
            profile.long_term_tags.append(tag)
            await self._storage.save_group_profile(profile)
            logger.info(f"添加群聊长期标签: {group_id} -> {tag}")
    
    async def add_blacklist_topic(
        self,
        group_id: str,
        topic: str
    ) -> None:
        """添加禁忌话题
        
        禁忌话题是群聊中不应该讨论的话题，用于指导 LLM 避免相关内容。
        
        Args:
            group_id: 群聊ID
            topic: 禁忌话题
        
        Examples:
            >>> await manager.add_blacklist_topic("group_123", "政治")
        """
        profile = await self.get_or_create(group_id)
        
        if topic not in profile.blacklist_topics:
            profile.blacklist_topics.append(topic)
            await self._storage.save_group_profile(profile)
            logger.info(f"添加群聊禁忌话题: {group_id} -> {topic}")
