"""统计 API 测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from iris_memory.web.routes.stats import stats_bp


@pytest.fixture
def mock_component_manager():
    """模拟组件管理器"""
    manager = Mock()
    manager.status = Mock()
    manager.status.is_module_available = Mock(return_value=True)
    manager.status.get_available_modules = Mock(return_value=["l1_buffer", "l2_memory", "l3_kg"])
    return manager


@pytest.fixture
def mock_l1_buffer():
    """模拟 L1 缓冲组件"""
    buffer = Mock()
    buffer.get_token_count = AsyncMock(return_value={
        "total_tokens": 1500,
        "input_tokens": 1000,
        "output_tokens": 500,
        "message_count": 10
    })
    buffer.get_capacity = AsyncMock(return_value={
        "current": 1500,
        "max": 5000,
        "percentage": 30.0
    })
    return buffer


@pytest.fixture
def mock_l2_memory():
    """模拟 L2 记忆组件"""
    memory = Mock()
    memory.get_stats = AsyncMock(return_value={
        "total_memories": 150,
        "groups_count": 5,
        "avg_per_group": 30,
        "oldest_memory": "2026-03-01T00:00:00Z",
        "newest_memory": "2026-03-29T21:00:00Z"
    })
    return memory


@pytest.fixture
def mock_l3_kg():
    """模拟 L3 知识图谱组件"""
    kg = Mock()
    kg.get_stats = AsyncMock(return_value={
        "total_nodes": 50,
        "total_edges": 120,
        "node_types": {
            "concept": 20,
            "entity": 15,
            "event": 15
        },
        "edge_types": {
            "related_to": 80,
            "caused_by": 40
        }
    })
    return kg


class TestStatsAPI:
    """统计 API 测试"""

    @pytest.mark.asyncio
    async def test_get_token_stats_success(self, mock_component_manager, mock_l1_buffer):
        """测试成功获取 Token 统计"""
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.stats.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_l1_buffer
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/token')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["total_tokens"] == 1500
                assert data["data"]["message_count"] == 10

    @pytest.mark.asyncio
    async def test_get_memory_stats_success(self, mock_component_manager, mock_l2_memory):
        """测试成功获取记忆统计"""
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.stats.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_l2_memory
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/memory')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["total_memories"] == 150
                assert data["data"]["groups_count"] == 5

    @pytest.mark.asyncio
    async def test_get_knowledge_graph_stats_success(self, mock_component_manager, mock_l3_kg):
        """测试成功获取知识图谱统计"""
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.stats.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            mock_component_manager.get_component.return_value = mock_l3_kg
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/knowledge-graph')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert data["data"]["total_nodes"] == 50
                assert data["data"]["total_edges"] == 120

    @pytest.mark.asyncio
    async def test_get_system_overview_success(
        self,
        mock_component_manager,
        mock_l1_buffer,
        mock_l2_memory,
        mock_l3_kg
    ):
        """测试成功获取系统概览"""
        def get_component_side_effect(module_name):
            if module_name == "l1_buffer":
                return mock_l1_buffer
            elif module_name == "l2_memory":
                return mock_l2_memory
            elif module_name == "l3_kg":
                return mock_l3_kg
            return None
        
        mock_component_manager.get_component = Mock(side_effect=get_component_side_effect)
        
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.stats.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/overview')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                assert "l1_buffer" in data["data"]
                assert "l2_memory" in data["data"]
                assert "l3_kg" in data["data"]

    @pytest.mark.asyncio
    async def test_component_unavailable(self, mock_component_manager):
        """测试组件不可用时的响应"""
        mock_component_manager.status.is_module_available.return_value = False
        
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager):
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/token')
                
                assert response.status_code == 503
                data = await response.get_json()
                assert data["success"] is False
                assert "组件不可用" in data["error"]

    @pytest.mark.asyncio
    async def test_partial_availability(
        self,
        mock_component_manager,
        mock_l1_buffer
    ):
        """测试部分组件可用"""
        def is_available_side_effect(module_name):
            return module_name == "l1_buffer"
        
        mock_component_manager.status.is_module_available = Mock(side_effect=is_available_side_effect)
        mock_component_manager.get_component.return_value = mock_l1_buffer
        
        with patch('iris_memory.web.routes.stats.get_component_manager', return_value=mock_component_manager), \
             patch('iris_memory.web.routes.stats.get_config') as mock_config:
            
            mock_config.return_value.get.return_value = True
            
            from quart import Quart
            app = Quart(__name__)
            app.register_blueprint(stats_bp, url_prefix='/api/iris/stats')
            
            async with app.test_client() as client:
                response = await client.get('/api/iris/stats/overview')
                
                assert response.status_code == 200
                data = await response.get_json()
                assert data["success"] is True
                # L1 可用
                assert "l1_buffer" in data["data"]
                # L2/L3 不可用
                assert data["data"]["l2_memory"]["available"] is False
                assert data["data"]["l3_kg"]["available"] is False
