"""
Iris Tier Memory - 群聊画像管理器

封装群聊画像的业务逻辑。
支持三层更新频率和智能合并策略。
"""

from typing import List, Optional
from datetime import datetime

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .storage import ProfileStorage
from .models import (
    GroupProfile,
    FieldMeta,
    ProfileUpdateTracker,
    UpdateTier,
    merge_list_field,
)

logger = get_logger("profile")


class GroupProfileManager:
    """群聊画像管理器

    封装群聊画像的业务逻辑，提供：
    - 获取/创建画像
    - 更新简单字段（实时，无LLM）
    - 更新中期字段（LLM分析，按频率触发）
    - 更新长期字段（LLM分析，高置信度触发）
    - 智能合并：列表字段合并而非替换

    Attributes:
        _storage: 画像存储组件实例
    """

    def __init__(self, storage: ProfileStorage):
        self._storage = storage

    async def get_or_create(self, group_id: str) -> GroupProfile:
        """获取或创建群聊画像

        Args:
            group_id: 群聊ID

        Returns:
            群聊画像对象
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
        """更新简单字段（实时记录，无LLM）

        简单字段包括：当前话题、活跃用户列表、最近互动时间、群聊名称。

        Args:
            group_id: 群聊ID
            current_topic: 当前话题（可选）
            active_users: 活跃用户列表（可选）
            group_name: 群聊名称（可选）
        """
        profile = await self.get_or_create(group_id)

        name_changed = False
        if current_topic is not None:
            profile.current_topic = current_topic

        if active_users is not None:
            profile.active_users = active_users

        if group_name is not None:
            profile.group_name = group_name
            name_changed = True

        profile.last_interaction_time = datetime.now()

        await self._storage.save_group_profile(profile, increment_version=name_changed)
        logger.debug(f"更新群聊画像简单字段: {group_id}")

    async def update_from_analysis(
        self,
        group_id: str,
        interests: Optional[List[str]] = None,
        atmosphere_tags: Optional[List[str]] = None,
        common_expressions: Optional[List[str]] = None,
        active_time_slots: Optional[List[str]] = None,
        custom_fields: Optional[dict] = None,
        tier: UpdateTier = UpdateTier.MID,
        confidence: float = 0.7
    ) -> None:
        """从分析结果更新字段（LLM分析后调用）

        根据更新层级和置信度智能合并字段：
        - 列表字段：合并新旧值，新值优先
        - 长期字段：要求更高置信度才覆盖

        Args:
            group_id: 群聊ID
            interests: 群聊兴趣点列表
            atmosphere_tags: 氛围标签列表
            common_expressions: 常用语/梗列表
            active_time_slots: 活跃时段列表
            custom_fields: 自定义字段字典
            tier: 更新层级
            confidence: 本次分析的整体置信度
        """
        profile = await self.get_or_create(group_id)
        updated = False

        if interests is not None:
            meta = profile.get_field_meta("interests")
            merged = merge_list_field(profile.interests, interests)
            if merged != profile.interests:
                profile.interests = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("interests", meta)
                updated = True

        if atmosphere_tags is not None:
            meta = profile.get_field_meta("atmosphere_tags")
            merged = merge_list_field(profile.atmosphere_tags, atmosphere_tags)
            if merged != profile.atmosphere_tags:
                profile.atmosphere_tags = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("atmosphere_tags", meta)
                updated = True

        if common_expressions is not None:
            meta = profile.get_field_meta("common_expressions")
            merged = merge_list_field(profile.common_expressions, common_expressions, max_items=30)
            if merged != profile.common_expressions:
                profile.common_expressions = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("common_expressions", meta)
                updated = True

        if active_time_slots is not None:
            meta = profile.get_field_meta("active_time_slots")
            merged = merge_list_field(profile.active_time_slots, active_time_slots)
            if merged != profile.active_time_slots:
                profile.active_time_slots = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("active_time_slots", meta)
                updated = True

        if custom_fields:
            for key, value in custom_fields.items():
                if key not in profile.custom_fields or not profile.custom_fields[key]:
                    profile.custom_fields[key] = value
                    updated = True

        tracker = profile.get_update_tracker()
        if tier == UpdateTier.MID:
            tracker.record_mid_update()
        elif tier == UpdateTier.LONG:
            tracker.record_long_update()
        profile.set_update_tracker(tracker)

        await self._storage.save_group_profile(profile, increment_version=updated)
        if updated:
            logger.info(f"从分析结果更新群聊画像: {group_id} (tier={tier.value})")

    async def update_long_term_from_analysis(
        self,
        group_id: str,
        long_term_tags: Optional[List[str]] = None,
        blacklist_topics: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        atmosphere_tags: Optional[List[str]] = None,
        custom_fields: Optional[dict] = None,
        confidence: float = 0.8
    ) -> None:
        """从长期分析结果更新字段

        长期字段要求更高置信度，且更难被覆盖。

        Args:
            group_id: 群聊ID
            long_term_tags: 核心特征标签
            blacklist_topics: 禁忌话题
            interests: 兴趣点（如有变化）
            atmosphere_tags: 氛围标签（如有变化）
            custom_fields: 自定义字段
            confidence: 置信度
        """
        profile = await self.get_or_create(group_id)
        updated = False

        if long_term_tags is not None:
            meta = profile.get_field_meta("long_term_tags")
            merged = merge_list_field(profile.long_term_tags, long_term_tags, max_items=10)
            if merged != profile.long_term_tags:
                profile.long_term_tags = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("long_term_tags", meta)
                updated = True

        if blacklist_topics is not None:
            for topic in blacklist_topics:
                if topic and topic not in profile.blacklist_topics:
                    profile.blacklist_topics.append(topic)
                    updated = True
            if updated:
                meta = profile.get_field_meta("blacklist_topics")
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("blacklist_topics", meta)

        if interests is not None:
            meta = profile.get_field_meta("interests")
            merged = merge_list_field(profile.interests, interests)
            if merged != profile.interests:
                profile.interests = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("interests", meta)
                updated = True

        if atmosphere_tags is not None:
            meta = profile.get_field_meta("atmosphere_tags")
            merged = merge_list_field(profile.atmosphere_tags, atmosphere_tags)
            if merged != profile.atmosphere_tags:
                profile.atmosphere_tags = merged
                meta.record_update(confidence, source="llm")
                profile.set_field_meta("atmosphere_tags", meta)
                updated = True

        if custom_fields:
            for key, value in custom_fields.items():
                if key not in profile.custom_fields or not profile.custom_fields[key]:
                    profile.custom_fields[key] = value
                    updated = True

        tracker = profile.get_update_tracker()
        tracker.record_long_update()
        profile.set_update_tracker(tracker)

        await self._storage.save_group_profile(profile, increment_version=updated)
        if updated:
            logger.info(f"从长期分析更新群聊画像: {group_id}")

    def should_update_mid(self, profile: GroupProfile) -> bool:
        """判断群聊画像是否需要中期更新

        Args:
            profile: 群聊画像

        Returns:
            是否需要更新
        """
        config = get_config()
        interval_summaries = config.get("profile_mid_update_interval_summaries") if hasattr(config, 'get') else 5
        interval_hours = config.get("profile_mid_update_interval_hours") if hasattr(config, 'get') else 24.0

        tracker = profile.get_update_tracker()
        return tracker.should_update_mid(interval_summaries, interval_hours)

    def should_update_long(self, profile: GroupProfile) -> bool:
        """判断群聊画像是否需要长期更新

        Args:
            profile: 群聊画像

        Returns:
            是否需要更新
        """
        config = get_config()
        interval_hours = config.get("profile_long_update_interval_hours") if hasattr(config, 'get') else 168.0

        tracker = profile.get_update_tracker()
        return tracker.should_update_long(interval_hours)

    async def add_long_term_tag(
        self,
        group_id: str,
        tag: str
    ) -> None:
        """添加长期标签（人工或高质量LLM更新）"""
        profile = await self.get_or_create(group_id)

        if tag not in profile.long_term_tags:
            profile.long_term_tags.append(tag)
            meta = profile.get_field_meta("long_term_tags")
            meta.record_update(1.0, source="manual")
            profile.set_field_meta("long_term_tags", meta)
            await self._storage.save_group_profile(profile)
            logger.info(f"添加群聊长期标签: {group_id} -> {tag}")

    async def add_blacklist_topic(
        self,
        group_id: str,
        topic: str
    ) -> None:
        """添加禁忌话题"""
        profile = await self.get_or_create(group_id)

        if topic not in profile.blacklist_topics:
            profile.blacklist_topics.append(topic)
            meta = profile.get_field_meta("blacklist_topics")
            meta.record_update(1.0, source="manual")
            profile.set_field_meta("blacklist_topics", meta)
            await self._storage.save_group_profile(profile)
            logger.info(f"添加群聊禁忌话题: {group_id} -> {topic}")
