"""画像数据模型测试"""

import pytest
from datetime import datetime

from iris_memory.profile.models import (
    GroupProfile,
    UserProfile,
    profile_to_dict,
    dict_to_group_profile,
    dict_to_user_profile
)


class TestGroupProfile:
    """群聊画像数据模型测试"""
    
    def test_create_group_profile(self):
        """测试创建群聊画像"""
        profile = GroupProfile(group_id="group_123")
        
        assert profile.group_id == "group_123"
        assert profile.group_name == ""
        assert profile.version == 1
        assert profile.current_topic == ""
        assert profile.interests == []
        assert profile.atmosphere_tags == []
    
    def test_group_profile_with_data(self):
        """测试带数据的群聊画像"""
        profile = GroupProfile(
            group_id="group_123",
            group_name="技术交流群",
            interests=["技术", "AI"],
            atmosphere_tags=["轻松", "技术范"]
        )
        
        assert profile.group_name == "技术交流群"
        assert profile.interests == ["技术", "AI"]
        assert profile.atmosphere_tags == ["轻松", "技术范"]
    
    def test_profile_to_dict(self):
        """测试画像转字典"""
        profile = GroupProfile(
            group_id="group_123",
            group_name="测试群",
            last_interaction_time=datetime(2026, 3, 29, 18, 0, 0)
        )
        
        data = profile_to_dict(profile)
        
        assert data["group_id"] == "group_123"
        assert data["group_name"] == "测试群"
        assert isinstance(data["last_interaction_time"], str)  # datetime 转为字符串
    
    def test_dict_to_group_profile(self):
        """测试字典转群聊画像"""
        data = {
            "group_id": "group_123",
            "group_name": "测试群",
            "version": 2,
            "interests": ["技术"],
            "last_interaction_time": "2026-03-29T18:00:00"
        }
        
        profile = dict_to_group_profile(data)
        
        assert profile.group_id == "group_123"
        assert profile.group_name == "测试群"
        assert profile.version == 2
        assert profile.interests == ["技术"]
        assert isinstance(profile.last_interaction_time, datetime)


class TestUserProfile:
    """用户画像数据模型测试"""
    
    def test_create_user_profile(self):
        """测试创建用户画像"""
        profile = UserProfile(user_id="user_456")
        
        assert profile.user_id == "user_456"
        assert profile.user_name == ""
        assert profile.version == 1
        assert profile.personality_tags == []
        assert profile.interests == []
    
    def test_user_profile_with_data(self):
        """测试带数据的用户画像"""
        profile = UserProfile(
            user_id="user_456",
            user_name="小明",
            personality_tags=["外向", "幽默"],
            interests=["编程", "游戏"]
        )
        
        assert profile.user_name == "小明"
        assert profile.personality_tags == ["外向", "幽默"]
        assert profile.interests == ["编程", "游戏"]
    
    def test_user_profile_to_dict(self):
        """测试用户画像转字典"""
        profile = UserProfile(
            user_id="user_456",
            user_name="小明",
            last_interaction_time=datetime(2026, 3, 29, 18, 0, 0)
        )
        
        data = profile_to_dict(profile)
        
        assert data["user_id"] == "user_456"
        assert data["user_name"] == "小明"
        assert isinstance(data["last_interaction_time"], str)
    
    def test_dict_to_user_profile(self):
        """测试字典转用户画像"""
        data = {
            "user_id": "user_456",
            "user_name": "小明",
            "version": 3,
            "personality_tags": ["外向"],
            "last_interaction_time": "2026-03-29T18:00:00"
        }
        
        profile = dict_to_user_profile(data)
        
        assert profile.user_id == "user_456"
        assert profile.user_name == "小明"
        assert profile.version == 3
        assert profile.personality_tags == ["外向"]
        assert isinstance(profile.last_interaction_time, datetime)
