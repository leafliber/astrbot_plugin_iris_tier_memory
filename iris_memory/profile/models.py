"""
Iris Tier Memory - 画像数据模型

定义群聊画像和用户画像的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


# ============================================================================
# 群聊画像
# ============================================================================

@dataclass
class GroupProfile:
    """群聊画像
    
    记录群聊的整体特征和行为模式。
    
    Attributes:
        group_id: 群聊ID
        group_name: 群聊名称
        version: 版本号（用于版本控制）
        
        current_topic: 当前所聊话题（短期，实时更新）
        last_interaction_time: 最近互动时间（短期）
        active_users: 活跃用户列表（短期）
        
        interests: 群聊兴趣点（中期，定时分析更新）
        active_time_slots: 活跃时段（中期）
        atmosphere_tags: 氛围标签（中期）
        common_expressions: 常用语/梗（中期）
        
        long_term_tags: 核心特征标签（长期）
        blacklist_topics: 禁忌话题（长期）
        
        custom_fields: 扩展字段
    
    Examples:
        >>> profile = GroupProfile(group_id="group_123")
        >>> profile.current_topic = "最近的AI技术进展"
        >>> profile.interests = ["技术", "编程", "AI"]
    """
    
    # 基础信息
    group_id: str
    group_name: str = ""
    version: int = 1  # 版本控制
    
    # 短期信息（实时更新）
    current_topic: str = ""  # 当前所聊话题
    last_interaction_time: Optional[datetime] = None  # 最近互动时间
    active_users: List[str] = field(default_factory=list)  # 活跃用户列表
    
    # 中期信息（定时分析更新）
    interests: List[str] = field(default_factory=list)  # 群聊兴趣点
    active_time_slots: List[str] = field(default_factory=list)  # 活跃时段
    atmosphere_tags: List[str] = field(default_factory=list)  # 氛围标签
    common_expressions: List[str] = field(default_factory=list)  # 常用语/梗
    
    # 长期标签（人工或高质量LLM更新）
    long_term_tags: List[str] = field(default_factory=list)  # 核心特征标签
    blacklist_topics: List[str] = field(default_factory=list)  # 禁忌话题
    
    # 扩展字段
    custom_fields: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# 用户画像
# ============================================================================

@dataclass
class UserProfile:
    """用户画像
    
    记录用户的个人特征和行为模式。
    
    Attributes:
        user_id: 用户ID
        user_name: 用户昵称
        version: 版本号（用于版本控制）
        
        historical_names: 历史曾用ID（历史记录，实时更新）
        last_interaction_time: 最近互动时间（历史记录）
        
        current_emotional_state: 当前情感状态（中期，定时分析更新）
        personality_tags: 性格标签（中期）
        interests: 兴趣爱好（中期）
        occupation: 职业/身份（中期）
        language_style: 常用语言风格（中期）
        
        bot_relationship: 对bot的称呼/关系设定（长期）
        important_dates: 重要纪念日（长期）
        taboo_topics: 禁忌话题（长期）
        important_events: 历史重要事件（长期）
        
        custom_fields: 扩展字段
    
    Examples:
        >>> profile = UserProfile(user_id="user_456")
        >>> profile.user_name = "小明"
        >>> profile.personality_tags = ["外向", "幽默"]
    """
    
    # 基础信息
    user_id: str
    user_name: str = ""
    version: int = 1  # 版本控制
    
    # 历史记录（实时更新）
    historical_names: List[str] = field(default_factory=list)  # 历史曾用ID
    last_interaction_time: Optional[datetime] = None
    
    # 中期信息（定时分析更新）
    current_emotional_state: str = ""  # 当前情感状态
    personality_tags: List[str] = field(default_factory=list)  # 性格标签
    interests: List[str] = field(default_factory=list)  # 兴趣爱好
    occupation: str = ""  # 职业/身份
    language_style: str = ""  # 常用语言风格
    
    # 长期信息
    bot_relationship: str = ""  # 对bot的称呼/关系设定
    important_dates: List[Dict[str, str]] = field(default_factory=list)  # 重要纪念日
    taboo_topics: List[str] = field(default_factory=list)  # 禁忌话题
    important_events: List[str] = field(default_factory=list)  # 历史重要事件
    
    # 扩展字段
    custom_fields: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# 辅助函数
# ============================================================================

def profile_to_dict(profile: GroupProfile | UserProfile) -> dict:
    """将画像对象转换为字典（处理datetime序列化）
    
    Args:
        profile: 画像对象（GroupProfile 或 UserProfile）
    
    Returns:
        可JSON序列化的字典
    
    Examples:
        >>> profile = GroupProfile(group_id="group_123")
        >>> data = profile_to_dict(profile)
        >>> isinstance(data, dict)
        True
    """
    data = {}
    for key, value in profile.__dict__.items():
        if isinstance(value, datetime):
            # datetime 转换为 ISO 格式字符串
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data


def dict_to_group_profile(data: dict) -> GroupProfile:
    """从字典创建群聊画像对象（处理datetime反序列化）
    
    Args:
        data: 字典数据
    
    Returns:
        GroupProfile 对象
    
    Examples:
        >>> data = {"group_id": "group_123", "version": 1}
        >>> profile = dict_to_group_profile(data)
        >>> profile.group_id
        'group_123'
    """
    # 处理 datetime 字段
    if "last_interaction_time" in data and isinstance(data["last_interaction_time"], str):
        data["last_interaction_time"] = datetime.fromisoformat(data["last_interaction_time"])
    
    return GroupProfile(**data)


def dict_to_user_profile(data: dict) -> UserProfile:
    """从字典创建用户画像对象（处理datetime反序列化）
    
    Args:
        data: 字典数据
    
    Returns:
        UserProfile 对象
    
    Examples:
        >>> data = {"user_id": "user_456", "version": 1}
        >>> profile = dict_to_user_profile(data)
        >>> profile.user_id
        'user_456'
    """
    # 处理 datetime 字段
    if "last_interaction_time" in data and isinstance(data["last_interaction_time"], str):
        data["last_interaction_time"] = datetime.fromisoformat(data["last_interaction_time"])
    
    return UserProfile(**data)
