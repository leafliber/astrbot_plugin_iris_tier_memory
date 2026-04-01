"""
Iris Tier Memory - 用户画像管理器

封装用户画像的业务逻辑。
"""

from typing import List, Optional, Dict
from datetime import datetime

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .storage import ProfileStorage
from .models import UserProfile

logger = get_logger("profile")


# ============================================================================
# 用户画像管理器
# ============================================================================

class UserProfileManager:
    """用户画像管理器
    
    封装用户画像的业务逻辑，提供：
    - 获取/创建画像
    - 更新简单字段（实时）
    - 更新复杂字段（定时分析）
    - 曾用名记录
    
    Attributes:
        _storage: 画像存储组件实例
    
    Examples:
        >>> storage = ProfileStorage(context)
        >>> manager = UserProfileManager(storage)
        >>> profile = await manager.get_or_create("user_456", "group_123")
        >>> await manager.update_simple_fields("user_456", user_name="小明")
    """
    
    def __init__(self, storage: ProfileStorage):
        """初始化用户画像管理器
        
        Args:
            storage: 画像存储组件实例
        """
        self._storage = storage
    
    async def get_or_create(
        self, 
        user_id: str,
        group_id: str = "default"
    ) -> UserProfile:
        """获取或创建用户画像
        
        如果画像不存在，创建一个新的空画像。
        根据群聊隔离配置决定 group_id：
        - 全局模式：group_id = "default"
        - 群聊隔离模式：group_id = 实际群聊ID
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID（全局模式传 "default"）
        
        Returns:
            用户画像对象
        
        Examples:
            >>> profile = await manager.get_or_create("user_456", "group_123")
            >>> profile.user_id
            'user_456'
        """
        profile = await self._storage.get_user_profile(user_id, group_id)
        
        if not profile:
            profile = UserProfile(user_id=user_id)
            mode = "全局" if group_id == "default" else f"群聊{group_id}"
            logger.info(f"创建新用户画像: {user_id} ({mode})")
        
        return profile
    
    async def update_simple_fields(
        self,
        user_id: str,
        group_id: str = "default",
        user_name: Optional[str] = None
    ) -> None:
        """更新简单字段（实时记录）
        
        简单字段包括：用户昵称、最近互动时间、曾用名。
        这些字段在总结完成后直接更新，无需 LLM 调用。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID（全局模式传 "default"）
            user_name: 用户昵称（可选）
        
        Examples:
            >>> await manager.update_simple_fields(
            ...     "user_456",
            ...     "group_123",
            ...     user_name="小明"
            ... )
        """
        profile = await self.get_or_create(user_id, group_id)
        
        # 记录曾用名
        name_changed = False
        if user_name and user_name != profile.user_name:
            if profile.user_name and profile.user_name not in profile.historical_names:
                profile.historical_names.append(profile.user_name)
            profile.user_name = user_name
            name_changed = True
            logger.debug(f"更新用户昵称: {user_id} -> {user_name}")
        
        # 更新最近互动时间
        profile.last_interaction_time = datetime.now()
        
        # 保存画像（昵称变化时增加版本号）
        await self._storage.save_user_profile(profile, group_id, increment_version=name_changed)
        logger.debug(f"更新用户画像简单字段: {user_id} (群聊: {group_id})")
    
    async def update_from_analysis(
        self,
        user_id: str,
        group_id: str,
        emotional_state: str,
        personality_tags: List[str],
        interests: List[str],
        occupation: Optional[str] = None,
        language_style: Optional[str] = None,
        custom_fields: Optional[dict] = None
    ) -> None:
        """从分析结果更新复杂字段（定时任务调用）
        
        复杂字段包括：情感状态、性格标签、兴趣爱好、职业、语言风格、自定义字段。
        这些字段通过 LLM 分析对话内容提取，由定时任务调用。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            emotional_state: 当前情感状态
            personality_tags: 性格标签列表
            interests: 兴趣爱好列表
            occupation: 职业/身份（可选）
            language_style: 语言风格（可选）
            custom_fields: 自定义字段字典（可选，LLM可自由添加）
        
        Examples:
            >>> await manager.update_from_analysis(
            ...     "user_456",
            ...     "group_123",
            ...     emotional_state="愉快",
            ...     personality_tags=["外向", "幽默"],
            ...     interests=["编程", "游戏"],
            ...     custom_fields={"skill_level": "高级", "tech_stack": "Python, JS"}
            ... )
        """
        profile = await self.get_or_create(user_id, group_id)
        
        # 更新复杂字段
        profile.current_emotional_state = emotional_state
        profile.personality_tags = personality_tags
        profile.interests = interests
        
        if occupation is not None:
            profile.occupation = occupation
        
        if language_style is not None:
            profile.language_style = language_style
        
        # 更新自定义字段（合并，不覆盖已有值）
        if custom_fields:
            profile.custom_fields.update(custom_fields)
            logger.debug(f"更新用户自定义字段: {list(custom_fields.keys())}")
        
        # 保存画像
        await self._storage.save_user_profile(profile, group_id)
        logger.info(f"从分析结果更新用户画像: {user_id} (群聊: {group_id})")
    
    async def set_bot_relationship(
        self,
        user_id: str,
        group_id: str,
        relationship: str
    ) -> None:
        """设置用户对 bot 的称呼/关系设定
        
        记录用户对 AI 助手的称呼或关系设定，用于个性化交互。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            relationship: 关系设定（如 "小助手"、"朋友"）
        
        Examples:
            >>> await manager.set_bot_relationship("user_456", "group_123", "小助手")
        """
        profile = await self.get_or_create(user_id, group_id)
        profile.bot_relationship = relationship
        await self._storage.save_user_profile(profile, group_id)
        logger.info(f"设置用户对bot的关系: {user_id} -> {relationship}")
    
    async def add_important_date(
        self,
        user_id: str,
        group_id: str,
        date: str,
        description: str
    ) -> None:
        """添加重要纪念日
        
        记录用户的重要日期，用于个性化提醒和互动。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            date: 日期（如 "01-01" 或 "2024-01-01"）
            description: 日期描述
        
        Examples:
            >>> await manager.add_important_date(
            ...     "user_456",
            ...     "group_123",
            ...     "01-01",
            ...     "新年"
            ... )
        """
        profile = await self.get_or_create(user_id, group_id)
        
        date_entry = {"date": date, "description": description}
        if date_entry not in profile.important_dates:
            profile.important_dates.append(date_entry)
            await self._storage.save_user_profile(profile, group_id)
            logger.info(f"添加用户重要日期: {user_id} -> {date} ({description})")
    
    async def add_taboo_topic(
        self,
        user_id: str,
        group_id: str,
        topic: str
    ) -> None:
        """添加禁忌话题
        
        禁忌话题是用户不愿意讨论的话题，用于指导 LLM 避免相关内容。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            topic: 禁忌话题
        
        Examples:
            >>> await manager.add_taboo_topic("user_456", "group_123", "个人隐私")
        """
        profile = await self.get_or_create(user_id, group_id)
        
        if topic not in profile.taboo_topics:
            profile.taboo_topics.append(topic)
            await self._storage.save_user_profile(profile, group_id)
            logger.info(f"添加用户禁忌话题: {user_id} -> {topic}")
    
    async def add_important_event(
        self,
        user_id: str,
        group_id: str,
        event: str
    ) -> None:
        """添加历史重要事件
        
        记录用户的重要事件，用于个性化互动。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            event: 重要事件描述
        
        Examples:
            >>> await manager.add_important_event(
            ...     "user_456",
            ...     "group_123",
            ...     "2024年加入了AI社区"
            ... )
        """
        profile = await self.get_or_create(user_id, group_id)
        
        if event not in profile.important_events:
            profile.important_events.append(event)
            await self._storage.save_user_profile(profile, group_id)
            logger.info(f"添加用户重要事件: {user_id} -> {event}")
