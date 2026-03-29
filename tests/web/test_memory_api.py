"""记忆 API 测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from iris_memory.web.routes.memory import memory_bp


@pytest.fixture
def mock_component_manager():
    """模拟组件管理器"""
    manager = Mock()
    manager.status = Mock()
    manager.status.is_module_available = Mock(return_value=True)
    return manager


@pytest.fixture
def mock_l2_memory():
    """模拟 L2 记忆组件"""
    memory = Mock()
    memory.search = AsyncMock(return_value=[
        {
            "id": "mem_1",
            "content": "测试记忆内容",
            "metadata": {
                "group_id": "group_1",
                "user_id": "user_1",
                "timestamp": "2026-03-29T21:00:00Z"
            },
            "distance": 0.15
        }
    ])
    return memory


class TestMemoryAPI:
    """记忆 API 测试"""

    @pytest.mark.asyncio
    async def test_search_l2_memory_success(self, mock_component_manager, mock_l2_memory):
        """测试成功搜索 L2 记忆"""
        with patch('iris_memory.web.routes.memory.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.memory.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_l2_memory
            
            # 模拟 Quart 请求
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(memory_bp, url_prefix='/api/iris/memory')
            
            async with app.test_client() as client:
                response = await client.post(
                    '/api/iris/memory/l2/search',
                    json={
                        "query": "测试查询",
                        "group_id": "group_1",
                        "limit": 10
                    }
                )
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert len(data["data"]["results"]) == 1

    @pytest.mark.asyncio
    async def test_search_l2_memory_component_unavailable(self, mock_component_manager):
        """测试组件不可用时的响应"""
        mock_component_manager.status.is_module_available.return_value = False
        
        with patch('iris_memory.web.routes.memory.get_component_manager', return_value=mock_component_manager):
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(memory_bp, url_prefix='/api/iris/memory')
            
            async with app.test_client() as client:
                response = await client.post(
                    '/api/iris/memory/l2/search',
                    json={"query": "测试查询"}
                )
                
                assert response.status_code == 503
                data = await response.get_json()
                assert data["success"] is False
                assert "L2 记忆库不可用" in data["error"]

    @pytest.mark.asyncio
    async def test_get_l1_buffer_success(self, mock_component_manager):
        """测试获取 L1 缓冲"""
        mock_l1 = Mock()
        mock_l1.get_messages = AsyncMock(return_value=[
            {"role": "user", "content": "测试消息"}
        ])
        
        with patch('iris_memory.web.routes.memory.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.memory.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_l1
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(memory_bp, url_prefix='/api/iris/memory')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/memory/l1/group_1')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert len(data["data"]["messages"]) == 1

    @pytest.mark.asyncio
    async def test_get_l3_knowledge_graph(self, mock_component_manager):
        """测试获取 L3 知识图谱"""
        mock_kg = Mock()
        mock_kg.get_graph = AsyncMock(return_value={
            "nodes": [
                {"id": "node_1", "label": "知识点", "type": "concept"}
            ],
            "edges": [
                {"source": "node_1", "target": "node_2", "relation": "related_to"}
            ]
        })
        
        with patch('iris_memory.web.routes.memory.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.memory.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_kg
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(memory_bp, url_prefix='/api/iris/memory')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/memory/l3/group_1')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert len(data["data"]["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_search_validation_missing_query(self):
        """测试搜索参数验证（缺少查询）"""
        from quart import Quart
        app = Quart(__name__)
        app.register_blueprint(memory_bp, url_prefix='/api/iris/memory')
        
        async with app.test_client() as client:
            response = await client.post(
                '/api/iris/memory/l2/search',
                json={"group_id": "group_1"}
            )
            
            assert response.status_code == 400
            data = await response.get_json()
            assert data["success"] is False
