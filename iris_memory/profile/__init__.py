"""
Iris Tier Memory - 画像系统模块

提供群聊画像和用户画像的存储、管理和分析功能。
"""

from .models import (
    GroupProfile,
    UserProfile,
    profile_to_dict,
    dict_to_group_profile,
    dict_to_user_profile
)
from .storage import ProfileStorage
from .group_profile import GroupProfileManager
from .user_profile import UserProfileManager
from .analyzer import ProfileAnalyzer

__all__ = [
    # 数据模型
    "GroupProfile",
    "UserProfile",
    "profile_to_dict",
    "dict_to_group_profile",
    "dict_to_user_profile",
    
    # 存储组件
    "ProfileStorage",
    
    # 管理器
    "GroupProfileManager",
    "UserProfileManager",
    
    # 分析器
    "ProfileAnalyzer",
]
