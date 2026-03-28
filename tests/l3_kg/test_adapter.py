"""L3 知识图谱适配器测试"""

import pytest
from pathlib import Path
import tempfile
import shutil

from iris_memory.l3_kg import GraphNode, GraphEdge, L3KGAdapter
from iris_memory.config import init_config


class TestL3KGAdapter:
    """L3KGAdapter 测试"""
    
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
        from iris_memory.config import Config
        from astrbot.api import AstrBotConfig
        
        # 创建最小配置
        config_dict = {
            "l3_kg": {
                "enable": True
            }
        }
        mock_config = AstrBotConfig(config_dict)
        
        # 初始化配置系统
        config = init_config(mock_config, temp_dir)
        
        # 创建适配器
        adapter = L3KGAdapter()
        await adapter.initialize()
        
        yield adapter
        
        # 清理
        await adapter.shutdown()
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter._is_available
        assert adapter.name == "l3_kg"
    
    @pytest.mark.asyncio
    async def test_add_node(self, adapter):
        """测试添加节点"""
        node = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="Alice is a software engineer"
        )
        node.id = node.generate_id()
        
        success = await adapter.add_node(node)
        assert success
        
        # 验证节点已添加
        stats = await adapter.get_stats()
        assert stats["node_count"] == 1
    
    @pytest.mark.asyncio
    async def test_add_edge(self, adapter):
        """测试添加边"""
        # 创建两个节点
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="Alice is a software engineer"
        )
        node1.id = node1.generate_id()
        
        node2 = GraphNode(
            id="",
            label="Event",
            name="Conference",
            content="AI Conference 2024"
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        # 创建边
        edge = GraphEdge(
            source_id=node1.id,
            target_id=node2.id,
            relation_type="ATTENDED"
        )
        
        success = await adapter.add_edge(edge)
        assert success
        
        # 验证边已添加
        stats = await adapter.get_stats()
        assert stats["edge_count"] == 1
    
    @pytest.mark.asyncio
    async def test_expand_from_nodes(self, adapter):
        """测试路径扩展检索"""
        # 创建测试数据
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="Alice is a software engineer"
        )
        node1.id = node1.generate_id()
        
        node2 = GraphNode(
            id="",
            label="Person",
            name="Bob",
            content="Bob is a data scientist"
        )
        node2.id = node2.generate_id()
        
        node3 = GraphNode(
            id="",
            label="Event",
            name="Conference",
            content="AI Conference 2024"
        )
        node3.id = node3.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        await adapter.add_node(node3)
        
        # 创建关系链：Alice -> Conference <- Bob
        edge1 = GraphEdge(
            source_id=node1.id,
            target_id=node3.id,
            relation_type="ATTENDED"
        )
        edge2 = GraphEdge(
            source_id=node2.id,
            target_id=node3.id,
            relation_type="ATTENDED"
        )
        
        await adapter.add_edge(edge1)
        await adapter.add_edge(edge2)
        
        # 从 Alice 出发进行路径扩展
        nodes, edges = await adapter.expand_from_nodes(
            node_ids=[node1.id],
            max_depth=2
        )
        
        # 应该找到 3 个节点和 2 条边
        assert len(nodes) == 3
        assert len(edges) == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, adapter):
        """测试获取统计信息"""
        stats = await adapter.get_stats()
        
        assert stats["available"]
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
