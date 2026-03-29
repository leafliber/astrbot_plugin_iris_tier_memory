"""画像 API 测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from iris_memory.web.routes.profile import profile_bp


@pytest.fixture
def mock_component_manager():
    """模拟组件管理器"""
    manager = Mock()
    manager.status = Mock()
    manager.status.is_module_available = Mock(return_value=True)
    return manager


@pytest.fixture
def mock_profile_storage():
    """模拟画像存储组件"""
    storage = Mock()
    storage.get_group_profile = AsyncMock(return_value={
        "group_id": "group_1",
        "group_name": "测试群聊",
        "atmosphere": "友好",
        "active_users": ["user_1", "user_2"],
        "topics": ["技术", "生活"],
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-03-29T21:00:00Z"
    })
    storage.update_group_profile = AsyncMock(return_value=True)
    storage.get_user_profile = AsyncMock(return_value={
        "user_id": "user_1",
        "username": "测试用户",
        "personality": "开朗",
        "interests": ["编程", "游戏"],
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-03-29T21:00:00Z"
    })
    storage.update_user_profile = AsyncMock(return_value=True)
    return storage


class TestProfileAPI:
    """画像 API 测试"""

    @pytest.mark.asyncio
    async def test_get_group_profile_success(self, mock_component_manager, mock_profile_storage):
        """测试成功获取群聊画像"""
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.profile.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_profile_storage
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/profile/group/group_1')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["group_id"] == "group_1"
                assert data["data"]["group_name"] == "测试群聊"

    @pytest.mark.asyncio
    async def test_update_group_profile_success(self, mock_component_manager, mock_profile_storage):
        """测试成功更新群聊画像"""
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.profile.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_profile_storage
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.put(
                    '/api/iris/profile/group/group_1',
                    json={
                        "atmosphere": "活跃",
                        "topics": ["技术", "游戏", "生活"]
                    }
                )
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["updated"] is True

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, mock_component_manager, mock_profile_storage):
        """测试成功获取用户画像"""
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.profile.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_profile_storage
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/profile/user/user_1')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["user_id"] == "user_1"
                assert data["data"]["username"] == "测试用户"

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, mock_component_manager, mock_profile_storage):
        """测试成功更新用户画像"""
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.profile.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_profile_storage
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.put(
                    '/api/iris/profile/user/user_1',
                    json={
                        "personality": "内向",
                        "interests": ["阅读", "音乐"]
                    }
                )
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["updated"] is True

    @pytest.mark.asyncio
    async def test_component_unavailable(self, mock_component_manager):
        """测试组件不可用时的响应"""
        mock_component_manager.status.is_module_available.return_value = False
        
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager):
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/profile/group/group_1')
                
                assert response.status_code == 503
                data = await response.get_json()
                assert data["success"] is False
                assert "画像存储不可用" in data["error"]

    @pytest.mark.asyncio
    async def test_profile_not_found(self, mock_component_manager, mock_profile_storage):
        """测试画像不存在"""
        mock_profile_storage.get_group_profile = AsyncMock(return_value=None)
        
        with patch('iris_memory.web.routes.profile.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.profile.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_profile_storage
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(profile_bp, url_prefix='/api/iris/profile')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/profile/group/nonexistent')
                
                assert response.status_code == 404
                data = await response.get_json()
                assert data["success"] is False
                assert "不存在" in data["error"]
