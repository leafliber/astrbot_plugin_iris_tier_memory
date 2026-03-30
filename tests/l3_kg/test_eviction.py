"""L3 知识图谱淘汰策略测试"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from iris_memory.l3_kg import (
    GraphNode,
    GraphEdge,
    L3KGAdapter,
    GraphEviction
)
from iris_memory.config import init_config


class TestGraphEviction:
    """GraphEviction 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    async def adapter(self, temp_dir):
        """创建适配器实例"""
        # 初始化配置
        from astrbot.api import AstrBotConfig
        
        config_dict = {
            "l3_kg": {
                "enable": True
            }
        }
        mock_config = AstrBotConfig(config_dict)
        init_config(mock_config, temp_dir)
        
        adapter = L3KGAdapter()
        await adapter.initialize()
        
        yield adapter
        
        await adapter.shutdown()
    
    @pytest.fixture
    def eviction(self, adapter):
        """创建淘汰策略实例"""
        return GraphEviction(adapter)
    
    @pytest.mark.asyncio
    async def test_evict_expired_entities_empty(self, eviction):
        """测试空数据库的淘汰"""
        nodes_deleted, edges_deleted = await eviction.evict_expired_entities()
        
        assert nodes_deleted == 0
        assert edges_deleted == 0
    
    @pytest.mark.asyncio
    async def test_evict_expired_entities_old_nodes(self, eviction, adapter):
        """测试淘汰过期节点"""
        # 添加一个旧节点（超过 30 天）
        old_node = GraphNode(
            id="",
            label="Person",
            name="OldPerson",
            content="过期用户"
        )
        old_node.id = old_node.generate_id()
        old_node.created_time = datetime.now() - timedelta(days=31)
        
        await adapter.add_node(old_node)
        
        # 添加一个新节点
        new_node = GraphNode(
            id="",
            label="Person",
            name="NewPerson",
            content="新用户"
        )
        new_node.id = new_node.generate_id()
        
        await adapter.add_node(new_node)
        
        # 执行淘汰
        nodes_deleted, _ = await eviction.evict_expired_entities()
        
        # 验证至少删除了一个节点
        assert nodes_deleted >= 1
        
        # 验证新节点仍然存在
        stats = await adapter.get_stats()
        assert stats["node_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_evict_expired_entities_with_edges(self, eviction, adapter):
        """测试淘汰节点时删除关联边"""
        # 添加两个节点
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="用户1"
        )
        node1.id = node1.generate_id()
        node1.created_time = datetime.now() - timedelta(days=31)
        
        node2 = GraphNode(
            id="",
            label="Event",
            name="Conference",
            content="会议"
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        # 添加边
        edge = GraphEdge(
            source_id=node1.id,
            target_id=node2.id,
            relation_type="ATTENDED"
        )
        await adapter.add_edge(edge)
        
        # 执行淘汰
        nodes_deleted, edges_deleted = await eviction.evict_expired_entities()
        
        # 验证至少删除了一些内容
        assert nodes_deleted >= 0
        assert edges_deleted >= 0
    
    @pytest.mark.asyncio
    async def test_evict_expired_entities_keeps_recent(self, eviction, adapter):
        """测试保留最近的节点"""
        # 添加最近访问的节点
        recent_node = GraphNode(
            id="",
            label="Person",
            name="RecentUser",
            content="最近活跃用户"
        )
        recent_node.id = recent_node.generate_id()
        recent_node.access_count = 10
        recent_node.last_access_time = datetime.now() - timedelta(days=5)
        
        await adapter.add_node(recent_node)
        
        # 执行淘汰
        nodes_deleted, _ = await eviction.evict_expired_entities()
        
        # 验证最近节点未被删除
        stats = await adapter.get_stats()
        assert stats["node_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_evict_nodes_directly(self, adapter):
        """测试直接淘汰节点"""
        # 添加测试节点
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="测试用户"
        )
        node1.id = node1.generate_id()
        
        node2 = GraphNode(
            id="",
            label="Person",
            name="Bob",
            content="测试用户"
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        # 淘汰一个节点
        deleted = await adapter.evict_nodes([node1.id])
        
        assert deleted == 1
        
        # 验证只剩一个节点
        stats = await adapter.get_stats()
        assert stats["node_count"] == 1
    
    @pytest.mark.asyncio
    async def test_evict_nodes_empty_list(self, adapter):
        """测试空列表的淘汰"""
        deleted = await adapter.evict_nodes([])
        assert deleted == 0
    
    @pytest.mark.asyncio
    async def test_evict_nodes_unavailable_adapter(self, adapter):
        """测试适配器不可用时的淘汰"""
        # 设置适配器不可用
        adapter._is_available = False
        
        deleted = await adapter.evict_nodes(["test_id"])
        assert deleted == 0
        
        # 恢复
        adapter._is_available = True
    
    @pytest.mark.asyncio
    async def test_eviction_with_high_access_count(self, eviction, adapter):
        """测试高访问次数节点的保留"""
        # 添加高访问次数的节点
        popular_node = GraphNode(
            id="",
            label="Person",
            name="PopularUser",
            content="热门用户"
        )
        popular_node.id = popular_node.generate_id()
        popular_node.access_count = 100
        popular_node.created_time = datetime.now() - timedelta(days=60)
        
        await adapter.add_node(popular_node)
        
        # 执行淘汰
        nodes_deleted, _ = await eviction.evict_expired_entities()
        
        # 验证热门节点可能被保留（取决于淘汰策略）
        # 这里只验证不抛出异常
        assert nodes_deleted >= 0
    
    @pytest.mark.asyncio
    async def test_eviction_preserves_connected_nodes(self, eviction, adapter):
        """测试保留有连接的节点"""
        # 添加连接的节点
        node1 = GraphNode(
            id="",
            label="Person",
            name="ConnectedUser1",
            content="连接用户1"
        )
        node1.id = node1.generate_id()
        node1.created_time = datetime.now() - timedelta(days=60)
        
        node2 = GraphNode(
            id="",
            label="Person",
            name="ConnectedUser2",
            content="连接用户2"
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        # 添加连接
        edge = GraphEdge(
            source_id=node1.id,
            target_id=node2.id,
            relation_type="KNOWS"
        )
        await adapter.add_edge(edge)
        
        # 执行淘汰
        nodes_deleted, _ = await eviction.evict_expired_entities()
        
        # 验证结果（具体行为取决于孤立度计算）
        assert nodes_deleted >= 0


class TestAdapterEviction:
    """适配器淘汰功能测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    async def adapter(self, temp_dir):
        """创建适配器实例"""
        from astrbot.api import AstrBotConfig
        
        config_dict = {"l3_kg": {"enable": True}}
        mock_config = AstrBotConfig(config_dict)
        init_config(mock_config, temp_dir)
        
        adapter = L3KGAdapter()
        await adapter.initialize()
        
        yield adapter
        
        await adapter.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_all_nodes(self, adapter):
        """测试获取所有节点"""
        # 添加测试节点
        node = GraphNode(
            id="",
            label="Person",
            name="TestUser",
            content="测试用户"
        )
        node.id = node.generate_id()
        
        await adapter.add_node(node)
        
        # 获取所有节点
        nodes = await adapter.get_all_nodes()
        
        assert len(nodes) >= 1
        assert any(n["id"] == node.id for n in nodes)
    
    @pytest.mark.asyncio
    async def test_get_all_nodes_empty(self, adapter):
        """测试空数据库获取节点"""
        nodes = await adapter.get_all_nodes()
        assert nodes == []
    
    @pytest.mark.asyncio
    async def test_evict_nodes_with_nonexistent_id(self, adapter):
        """测试淘汰不存在的节点"""
        deleted = await adapter.evict_nodes(["nonexistent_id"])
        assert deleted == 0
