"""
Iris Tier Memory - 画像数据模型

定义群聊画像和用户画像的数据结构。
支持三层更新频率和字段置信度管理。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union
from datetime import datetime
from enum import Enum


class UpdateTier(Enum):
    """字段更新层级
    
    短期字段：每次总结后规则更新，无需LLM
    中期字段：按时间间隔或总结次数触发LLM分析
    长期字段：仅检测到显著新信息时更新，需高置信度
    """
    SHORT = "short"
    MID = "mid"
    LONG = "long"


@dataclass
class FieldMeta:
    """字段元数据
    
    跟踪单个字段的置信度和更新历史。
    
    Attributes:
        confidence: 置信度 0.0~1.0，越高越可靠
        last_updated: 最近更新时间
        update_count: 累计更新次数
        source: 最近一次更新来源（rule/llm/manual）
    """
    confidence: float = 0.0
    last_updated: Optional[datetime] = None
    update_count: int = 0
    source: str = ""

    def should_update(self, tier: UpdateTier, min_confidence: float = 0.0) -> bool:
        """判断字段是否需要更新

        Args:
            tier: 字段更新层级
            min_confidence: 最低置信度阈值，低于此值需要更新

        Returns:
            是否需要更新
        """
        if self.confidence < min_confidence:
            return True
        if self.update_count == 0:
            return True
        if tier == UpdateTier.SHORT:
            return True
        return False

    def record_update(self, confidence: float, source: str = "rule") -> None:
        """记录一次更新

        Args:
            confidence: 本次更新置信度
            source: 更新来源
        """
        self.confidence = confidence
        self.last_updated = datetime.now()
        self.update_count += 1
        self.source = source


@dataclass
class ProfileUpdateTracker:
    """画像更新追踪器

    跟踪各层级字段的更新状态，用于控制更新频率。

    Attributes:
        summary_count_since_mid_update: 自上次中期更新以来的总结次数
        last_mid_update_time: 上次中期更新时间
        last_long_update_time: 上次长期更新时间
    """
    summary_count_since_mid_update: int = 0
    last_mid_update_time: Optional[datetime] = None
    last_long_update_time: Optional[datetime] = None

    def should_update_mid(self, interval_summaries: int = 5, interval_hours: float = 24.0) -> bool:
        """判断是否应该进行中期更新

        Args:
            interval_summaries: 每隔多少次总结触发一次中期更新
            interval_hours: 最长间隔小时数，超过此时间也触发更新

        Returns:
            是否应该更新
        """
        if self.summary_count_since_mid_update >= interval_summaries:
            return True
        if self.last_mid_update_time is None:
            return True
        if interval_hours > 0:
            elapsed = (datetime.now() - self.last_mid_update_time).total_seconds() / 3600
            if elapsed >= interval_hours:
                return True
        return False

    def should_update_long(self, interval_hours: float = 168.0) -> bool:
        """判断是否应该进行长期更新

        Args:
            interval_hours: 最长间隔小时数（默认7天）

        Returns:
            是否应该更新
        """
        if self.last_long_update_time is None:
            return True
        if interval_hours > 0:
            elapsed = (datetime.now() - self.last_long_update_time).total_seconds() / 3600
            if elapsed >= interval_hours:
                return True
        return False

    def record_mid_update(self) -> None:
        """记录中期更新"""
        self.summary_count_since_mid_update = 0
        self.last_mid_update_time = datetime.now()

    def record_long_update(self) -> None:
        """记录长期更新"""
        self.last_long_update_time = datetime.now()

    def increment_summary_count(self) -> None:
        """总结次数+1"""
        self.summary_count_since_mid_update += 1


# ============================================================================
# 群聊画像
# ============================================================================

@dataclass
class GroupProfile:
    """群聊画像

    记录群聊的整体特征和行为模式。
    支持三层更新频率和字段置信度管理。

    Attributes:
        group_id: 群聊ID
        group_name: 群聊名称
        version: 版本号（用于版本控制）

        current_topic: 当前所聊话题（短期，规则更新）
        last_interaction_time: 最近互动时间（短期）
        active_users: 活跃用户列表（短期）

        interests: 群聊兴趣点（中期，LLM分析更新）
        active_time_slots: 活跃时段（中期）
        atmosphere_tags: 氛围标签（中期）
        common_expressions: 常用语/梗（中期）

        long_term_tags: 核心特征标签（长期）
        blacklist_topics: 禁忌话题（长期）

        custom_fields: 扩展字段

        field_meta: 各字段元数据（置信度、更新时间等）
        update_tracker: 更新追踪器（控制更新频率）
    """

    group_id: str
    group_name: str = ""
    version: int = 1

    current_topic: str = ""
    last_interaction_time: Optional[datetime] = None
    active_users: List[str] = field(default_factory=list)

    interests: List[str] = field(default_factory=list)
    active_time_slots: List[str] = field(default_factory=list)
    atmosphere_tags: List[str] = field(default_factory=list)
    common_expressions: List[str] = field(default_factory=list)

    long_term_tags: List[str] = field(default_factory=list)
    blacklist_topics: List[str] = field(default_factory=list)

    custom_fields: Dict[str, str] = field(default_factory=dict)

    field_meta: Dict[str, Dict] = field(default_factory=dict)
    update_tracker: Dict = field(default_factory=dict)

    def get_update_tracker(self) -> ProfileUpdateTracker:
        """获取更新追踪器（从dict恢复）"""
        if not self.update_tracker:
            return ProfileUpdateTracker()
        tracker = ProfileUpdateTracker()
        data = self.update_tracker
        tracker.summary_count_since_mid_update = data.get("summary_count_since_mid_update", 0)
        if data.get("last_mid_update_time"):
            if isinstance(data["last_mid_update_time"], str):
                tracker.last_mid_update_time = datetime.fromisoformat(data["last_mid_update_time"])
            elif isinstance(data["last_mid_update_time"], datetime):
                tracker.last_mid_update_time = data["last_mid_update_time"]
        if data.get("last_long_update_time"):
            if isinstance(data["last_long_update_time"], str):
                tracker.last_long_update_time = datetime.fromisoformat(data["last_long_update_time"])
            elif isinstance(data["last_long_update_time"], datetime):
                tracker.last_long_update_time = data["last_long_update_time"]
        return tracker

    def set_update_tracker(self, tracker: ProfileUpdateTracker) -> None:
        """保存更新追踪器（转为dict存储）"""
        self.update_tracker = {
            "summary_count_since_mid_update": tracker.summary_count_since_mid_update,
            "last_mid_update_time": tracker.last_mid_update_time.isoformat() if tracker.last_mid_update_time else None,
            "last_long_update_time": tracker.last_long_update_time.isoformat() if tracker.last_long_update_time else None,
        }

    def get_field_meta(self, field_name: str) -> FieldMeta:
        """获取字段元数据"""
        if field_name not in self.field_meta:
            return FieldMeta()
        data = self.field_meta[field_name]
        meta = FieldMeta()
        meta.confidence = data.get("confidence", 0.0)
        meta.update_count = data.get("update_count", 0)
        meta.source = data.get("source", "")
        if data.get("last_updated"):
            if isinstance(data["last_updated"], str):
                meta.last_updated = datetime.fromisoformat(data["last_updated"])
            elif isinstance(data["last_updated"], datetime):
                meta.last_updated = data["last_updated"]
        return meta

    def set_field_meta(self, field_name: str, meta: FieldMeta) -> None:
        """设置字段元数据"""
        self.field_meta[field_name] = {
            "confidence": meta.confidence,
            "last_updated": meta.last_updated.isoformat() if meta.last_updated else None,
            "update_count": meta.update_count,
            "source": meta.source,
        }

    FIELD_TIERS: Dict[str, UpdateTier] = field(default_factory=lambda: {
        "current_topic": UpdateTier.SHORT,
        "active_users": UpdateTier.SHORT,
        "interests": UpdateTier.MID,
        "active_time_slots": UpdateTier.MID,
        "atmosphere_tags": UpdateTier.MID,
        "common_expressions": UpdateTier.MID,
        "long_term_tags": UpdateTier.LONG,
        "blacklist_topics": UpdateTier.LONG,
    })


# ============================================================================
# 用户画像
# ============================================================================

@dataclass
class UserProfile:
    """用户画像

    记录用户的个人特征和行为模式。
    支持三层更新频率和字段置信度管理。

    Attributes:
        user_id: 用户ID
        user_name: 用户昵称
        version: 版本号（用于版本控制）

        historical_names: 历史曾用ID（实时更新）
        last_interaction_time: 最近互动时间（实时更新）

        current_emotional_state: 当前情感状态（短期，规则更新）
        personality_tags: 性格标签（中期，LLM分析更新）
        interests: 兴趣爱好（中期）
        occupation: 职业/身份（长期）
        language_style: 常用语言风格（中期）

        bot_relationship: 对bot的称呼/关系设定（长期）
        important_dates: 重要纪念日（长期）
        taboo_topics: 禁忌话题（长期）
        important_events: 历史重要事件（长期）

        custom_fields: 扩展字段

        field_meta: 各字段元数据（置信度、更新时间等）
        update_tracker: 更新追踪器（控制更新频率）
    """

    user_id: str
    user_name: str = ""
    version: int = 1

    historical_names: List[str] = field(default_factory=list)
    last_interaction_time: Optional[datetime] = None

    current_emotional_state: str = ""
    personality_tags: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    occupation: str = ""
    language_style: str = ""

    bot_relationship: str = ""
    important_dates: List[Dict[str, str]] = field(default_factory=list)
    taboo_topics: List[str] = field(default_factory=list)
    important_events: List[str] = field(default_factory=list)

    custom_fields: Dict[str, str] = field(default_factory=dict)

    field_meta: Dict[str, Dict] = field(default_factory=dict)
    update_tracker: Dict = field(default_factory=dict)

    def get_update_tracker(self) -> ProfileUpdateTracker:
        """获取更新追踪器（从dict恢复）"""
        if not self.update_tracker:
            return ProfileUpdateTracker()
        tracker = ProfileUpdateTracker()
        data = self.update_tracker
        tracker.summary_count_since_mid_update = data.get("summary_count_since_mid_update", 0)
        if data.get("last_mid_update_time"):
            if isinstance(data["last_mid_update_time"], str):
                tracker.last_mid_update_time = datetime.fromisoformat(data["last_mid_update_time"])
            elif isinstance(data["last_mid_update_time"], datetime):
                tracker.last_mid_update_time = data["last_mid_update_time"]
        if data.get("last_long_update_time"):
            if isinstance(data["last_long_update_time"], str):
                tracker.last_long_update_time = datetime.fromisoformat(data["last_long_update_time"])
            elif isinstance(data["last_long_update_time"], datetime):
                tracker.last_long_update_time = data["last_long_update_time"]
        return tracker

    def set_update_tracker(self, tracker: ProfileUpdateTracker) -> None:
        """保存更新追踪器（转为dict存储）"""
        self.update_tracker = {
            "summary_count_since_mid_update": tracker.summary_count_since_mid_update,
            "last_mid_update_time": tracker.last_mid_update_time.isoformat() if tracker.last_mid_update_time else None,
            "last_long_update_time": tracker.last_long_update_time.isoformat() if tracker.last_long_update_time else None,
        }

    def get_field_meta(self, field_name: str) -> FieldMeta:
        """获取字段元数据"""
        if field_name not in self.field_meta:
            return FieldMeta()
        data = self.field_meta[field_name]
        meta = FieldMeta()
        meta.confidence = data.get("confidence", 0.0)
        meta.update_count = data.get("update_count", 0)
        meta.source = data.get("source", "")
        if data.get("last_updated"):
            if isinstance(data["last_updated"], str):
                meta.last_updated = datetime.fromisoformat(data["last_updated"])
            elif isinstance(data["last_updated"], datetime):
                meta.last_updated = data["last_updated"]
        return meta

    def set_field_meta(self, field_name: str, meta: FieldMeta) -> None:
        """设置字段元数据"""
        self.field_meta[field_name] = {
            "confidence": meta.confidence,
            "last_updated": meta.last_updated.isoformat() if meta.last_updated else None,
            "update_count": meta.update_count,
            "source": meta.source,
        }

    FIELD_TIERS: Dict[str, UpdateTier] = field(default_factory=lambda: {
        "current_emotional_state": UpdateTier.SHORT,
        "personality_tags": UpdateTier.MID,
        "interests": UpdateTier.MID,
        "language_style": UpdateTier.MID,
        "occupation": UpdateTier.LONG,
        "bot_relationship": UpdateTier.LONG,
        "important_dates": UpdateTier.LONG,
        "taboo_topics": UpdateTier.LONG,
        "important_events": UpdateTier.LONG,
    })


# ============================================================================
# 辅助函数
# ============================================================================

def profile_to_dict(profile: Union[GroupProfile, UserProfile]) -> dict:
    """将画像对象转换为字典（处理datetime序列化）

    Args:
        profile: 画像对象（GroupProfile 或 UserProfile）

    Returns:
        可JSON序列化的字典
    """
    data = {}
    for key, value in profile.__dict__.items():
        if key == "FIELD_TIERS":
            continue
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, UpdateTier):
            data[key] = value.value
        else:
            data[key] = value
    return data


def dict_to_group_profile(data: dict) -> GroupProfile:
    """从字典创建群聊画像对象（处理datetime反序列化）

    兼容旧版数据：缺少 field_meta 和 update_tracker 时使用默认值。

    Args:
        data: 字典数据

    Returns:
        GroupProfile 对象
    """
    if "last_interaction_time" in data and isinstance(data["last_interaction_time"], str):
        data["last_interaction_time"] = datetime.fromisoformat(data["last_interaction_time"])

    data.pop("FIELD_TIERS", None)

    valid_fields = {f.name for f in GroupProfile.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}

    return GroupProfile(**filtered)


def dict_to_user_profile(data: dict) -> UserProfile:
    """从字典创建用户画像对象（处理datetime反序列化）

    兼容旧版数据：缺少 field_meta 和 update_tracker 时使用默认值。

    Args:
        data: 字典数据

    Returns:
        UserProfile 对象
    """
    if "last_interaction_time" in data and isinstance(data["last_interaction_time"], str):
        data["last_interaction_time"] = datetime.fromisoformat(data["last_interaction_time"])

    data.pop("FIELD_TIERS", None)

    valid_fields = {f.name for f in UserProfile.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}

    return UserProfile(**filtered)


def merge_list_field(
    existing: List[str],
    new_values: List[str],
    max_items: int = 20
) -> List[str]:
    """智能合并列表字段

    新值优先，去重，保留最多 max_items 项。
    新值排在前面，旧值追加在后面。

    Args:
        existing: 现有列表
        new_values: 新值列表
        max_items: 最大保留项数

    Returns:
        合并后的列表
    """
    if not new_values:
        return existing

    merged = list(new_values)
    seen = set(new_values)

    for item in existing:
        if item not in seen:
            merged.append(item)
            seen.add(item)

    return merged[:max_items]


def should_overwrite_field(
    existing_value,
    new_value,
    existing_confidence: float,
    new_confidence: float,
    min_confidence_gap: float = 0.2
) -> bool:
    """判断是否应该用新值覆盖旧值

    置信度显著更高时才覆盖，避免频繁小幅变动。

    Args:
        existing_value: 现有值
        new_value: 新值
        existing_confidence: 现有置信度
        new_confidence: 新置信度
        min_confidence_gap: 最小置信度差距

    Returns:
        是否应该覆盖
    """
    if not existing_value:
        return True
    if not new_value:
        return False
    if existing_value == new_value:
        return False
    if new_confidence > existing_confidence + min_confidence_gap:
        return True
    if existing_confidence < 0.3:
        return True
    return False
