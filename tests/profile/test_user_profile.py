"""用户画像管理器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from iris_memory.profile.user_profile import UserProfileManager
from iris_memory.profile.models import UserProfile
from iris_memory.profile.storage import ProfileStorage


class TestUserProfileManager:
    """用户画像管理器测试"""
    
    @pytest.fixture
    def mock_storage(self):
        """创建模拟的 ProfileStorage"""
        storage = MagicMock(spec=ProfileStorage)
        storage.get_user_profile = AsyncMock()
        storage.save_user_profile = AsyncMock()
        return storage
    
    @pytest.fixture
    def manager(self, mock_storage):
        """创建 UserProfileManager 实例"""
        return UserProfileManager(mock_storage)
    
    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, manager, mock_storage):
        """测试获取已存在的用户画像"""
        existing_profile = UserProfile(
            user_id="user_456",
            user_name="小明"
        )
        mock_storage.get_user_profile.return_value = existing_profile
        
        profile = await manager.get_or_create("user_456", "group_123")
        
        assert profile.user_id == "user_456"
        assert profile.user_name == "小明"
        mock_storage.get_user_profile.assert_called_once_with("user_456", "group_123")
    
    @pytest.mark.asyncio
    async def test_get_or_create_new(self, manager, mock_storage):
        """测试创建新的用户画像"""
        mock_storage.get_user_profile.return_value = None
        
        profile = await manager.get_or_create("user_456", "group_123")
        
        assert profile.user_id == "user_456"
        assert profile.user_name == ""
        mock_storage.get_user_profile.assert_called_once_with("user_456", "group_123")
    
    @pytest.mark.asyncio
    async def test_update_simple_fields(self, manager, mock_storage):
        """测试更新简单字段"""
        existing_profile = UserProfile(user_id="user_456")
        mock_storage.get_user_profile.return_value = existing_profile
        
        await manager.update_simple_fields(
            user_id="user_456",
            group_id="group_123",
            user_name="小明"
        )
        
        assert existing_profile.user_name == "小明"
        assert existing_profile.last_interaction_time is not None
        mock_storage.save_user_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_simple_fields_with_name_change(self, manager, mock_storage):
        """测试更新用户昵称时记录曾用名"""
        existing_profile = UserProfile(
            user_id="user_456",
            user_name="旧昵称"
        )
        mock_storage.get_user_profile.return_value = existing_profile
        
        await manager.update_simple_fields(
            user_id="user_456",
            group_id="group_123",
            user_name="新昵称"
        )
        
        assert existing_profile.user_name == "新昵称"
        assert "旧昵称" in existing_profile.historical_names
        mock_storage.save_user_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_from_analysis(self, manager, mock_storage):
        """测试从分析结果更新"""
        existing_profile = UserProfile(user_id="user_456")
        mock_storage.get_user_profile.return_value = existing_profile
        
        await manager.update_from_analysis(
            user_id="user_456",
            group_id="group_123",
            emotional_state="愉快",
            personality_tags=["外向", "幽默"],
            interests=["编程", "游戏"]
        )
        
        assert existing_profile.current_emotional_state == "愉快"
        assert existing_profile.personality_tags == ["外向", "幽默"]
        assert existing_profile.interests == ["编程", "游戏"]
        mock_storage.save_user_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_bot_relationship(self, manager, mock_storage):
        """测试设置对 bot 的关系"""
        existing_profile = UserProfile(user_id="user_456")
        mock_storage.get_user_profile.return_value = existing_profile
        
        await manager.set_bot_relationship("user_456", "group_123", "小助手")
        
        assert existing_profile.bot_relationship == "小助手"
        mock_storage.save_user_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_taboo_topic(self, manager, mock_storage):
        """测试添加禁忌话题"""
        existing_profile = UserProfile(user_id="user_456")
        mock_storage.get_user_profile.return_value = existing_profile
        
        await manager.add_taboo_topic("user_456", "group_123", "个人隐私")
        
        assert "个人隐私" in existing_profile.taboo_topics
        mock_storage.save_user_profile.assert_called_once()
