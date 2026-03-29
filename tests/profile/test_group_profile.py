"""群聊画像管理器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from iris_memory.profile.group_profile import GroupProfileManager
from iris_memory.profile.models import GroupProfile
from iris_memory.profile.storage import ProfileStorage


class TestGroupProfileManager:
    """群聊画像管理器测试"""
    
    @pytest.fixture
    def mock_storage(self):
        """创建模拟的 ProfileStorage"""
        storage = MagicMock(spec=ProfileStorage)
        storage.get_group_profile = AsyncMock()
        storage.save_group_profile = AsyncMock()
        return storage
    
    @pytest.fixture
    def manager(self, mock_storage):
        """创建 GroupProfileManager 实例"""
        return GroupProfileManager(mock_storage)
    
    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, manager, mock_storage):
        """测试获取已存在的群聊画像"""
        existing_profile = GroupProfile(
            group_id="group_123",
            group_name="测试群"
        )
        mock_storage.get_group_profile.return_value = existing_profile
        
        profile = await manager.get_or_create("group_123")
        
        assert profile.group_id == "group_123"
        assert profile.group_name == "测试群"
        mock_storage.get_group_profile.assert_called_once_with("group_123")
    
    @pytest.mark.asyncio
    async def test_get_or_create_new(self, manager, mock_storage):
        """测试创建新的群聊画像"""
        mock_storage.get_group_profile.return_value = None
        
        profile = await manager.get_or_create("group_123")
        
        assert profile.group_id == "group_123"
        assert profile.group_name == ""
        mock_storage.get_group_profile.assert_called_once_with("group_123")
    
    @pytest.mark.asyncio
    async def test_update_simple_fields(self, manager, mock_storage):
        """测试更新简单字段"""
        existing_profile = GroupProfile(group_id="group_123")
        mock_storage.get_group_profile.return_value = existing_profile
        
        await manager.update_simple_fields(
            group_id="group_123",
            current_topic="AI技术讨论",
            active_users=["user1", "user2"]
        )
        
        assert existing_profile.current_topic == "AI技术讨论"
        assert existing_profile.active_users == ["user1", "user2"]
        assert existing_profile.last_interaction_time is not None
        mock_storage.save_group_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_from_analysis(self, manager, mock_storage):
        """测试从分析结果更新"""
        existing_profile = GroupProfile(group_id="group_123")
        mock_storage.get_group_profile.return_value = existing_profile
        
        await manager.update_from_analysis(
            group_id="group_123",
            interests=["技术", "AI"],
            atmosphere_tags=["轻松", "技术范"],
            common_expressions=["yyds", "绝了"]
        )
        
        assert existing_profile.interests == ["技术", "AI"]
        assert existing_profile.atmosphere_tags == ["轻松", "技术范"]
        assert existing_profile.common_expressions == ["yyds", "绝了"]
        mock_storage.save_group_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_long_term_tag(self, manager, mock_storage):
        """测试添加长期标签"""
        existing_profile = GroupProfile(group_id="group_123")
        mock_storage.get_group_profile.return_value = existing_profile
        
        await manager.add_long_term_tag("group_123", "技术交流群")
        
        assert "技术交流群" in existing_profile.long_term_tags
        mock_storage.save_group_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_blacklist_topic(self, manager, mock_storage):
        """测试添加禁忌话题"""
        existing_profile = GroupProfile(group_id="group_123")
        mock_storage.get_group_profile.return_value = existing_profile
        
        await manager.add_blacklist_topic("group_123", "政治")
        
        assert "政治" in existing_profile.blacklist_topics
        mock_storage.save_group_profile.assert_called_once()
