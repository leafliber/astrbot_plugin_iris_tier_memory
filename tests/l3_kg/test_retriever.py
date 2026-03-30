"""L3 知识图谱检索器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil
import asyncio

from iris_memory.l3_kg import GraphRetriever, GraphNode, GraphEdge, L3KGAdapter
from iris_memory.config import init_config


class TestGraphRetriever:
    """GraphRetriever 测试"""
    
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
        
        config_dict = {
            "l3_kg": {
                "enable": True,
                "expansion_depth": 2,
                "timeout_ms": 1500
            }
        }
        mock_config = AstrBotConfig(config_dict)
        init_config(mock_config, temp_dir)
        
        adapter = L3KGAdapter()
        await adapter.initialize()
        
        yield adapter
        
        await adapter.shutdown()
    
    @pytest.fixture
    def retriever(self, adapter):
        """创建检索器实例"""
        return GraphRetriever(adapter)
    
    @pytest.mark.asyncio
    async def test_format_for_context_empty(self, retriever):
        """测试格式化空结果"""
        result = retriever.format_for_context([], [])
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_format_for_context_with_nodes(self, retriever):
        """测试格式化节点结果"""
        nodes = [
            {
                "id": "person_alice",
                "label": "Person",
                "name": "Alice",
                "content": "软件工程师"
            },
            {
                "id": "person_bob",
                "label": "Person",
                "name": "Bob",
                "content": "数据科学家"
            },
            {
                "id": "event_conf",
                "label": "Event",
                "name": "AI Conference",
                "content": "2024 AI 大会"
            }
        ]
        
        result = retriever.format_for_context(nodes, [])
        
        # 验证格式化结果
        assert "## 知识图谱关联信息" in result
        assert "### Person" in result
        assert "### Event" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "AI Conference" in result
    
    @pytest.mark.asyncio
    async def test_format_for_context_with_edges(self, retriever):
        """测试格式化边结果"""
        nodes = [
            {
                "id": "person_alice",
                "label": "Person",
                "name": "Alice",
                "content": "软件工程师"
            }
        ]
        
        edges = [
            {
                "source": "person_alice",
                "source_name": "Alice",
                "target": "event_conf",
                "target_name": "AI Conference",
                "relation_type": "ATTENDED"
            }
        ]
        
        result = retriever.format_for_context(nodes, edges)
        
        # 验证格式化结果
        assert "### 关系" in result
        assert "Alice" in result
        assert "AI Conference" in result
        assert "ATTENDED" in result
    
    @pytest.mark.asyncio
    async def test_format_for_context_groups_by_type(self, retriever):
        """测试按类型分组节点"""
        nodes = [
            {"label": "Person", "name": "Alice", "content": "描述1"},
            {"label": "Person", "name": "Bob", "content": "描述2"},
            {"label": "Event", "name": "会议", "content": "描述3"},
            {"label": "Person", "name": "Charlie", "content": "描述4"}
        ]
        
        result = retriever.format_for_context(nodes, [])
        
        # 验证分组
        lines = result.split("\n")
        
        # 找到 Person 和 Event 部分
        person_indices = [i for i, line in enumerate(lines) if "### Person" in line]
        event_indices = [i for i, line in enumerate(lines) if "### Event" in line]
        
        assert len(person_indices) == 1
        assert len(event_indices) == 1
    
    @pytest.mark.asyncio
    async def test_retrieve_with_expansion_empty_ids(self, retriever):
        """测试空节点 ID 列表"""
        nodes, edges = await retriever.retrieve_with_expansion([])
        
        # 应该返回空结果
        assert nodes == []
        assert edges == []
    
    @pytest.mark.asyncio
    async def test_retrieve_with_expansion_success(self, retriever, adapter):
        """测试路径扩展检索"""
        # 先添加一些测试数据
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="软件工程师"
        )
        node1.id = node1.generate_id()
        
        node2 = GraphNode(
            id="",
            label="Event",
            name="Conference",
            content="AI 大会"
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        edge = GraphEdge(
            source_id=node1.id,
            target_id=node2.id,
            relation_type="ATTENDED"
        )
        await adapter.add_edge(edge)
        
        # 执行检索
        nodes, edges = await retriever.retrieve_with_expansion([node1.id])
        
        # 验证结果（应该扩展到相关节点）
        assert len(nodes) >= 1  # 至少包含起始节点
    
    @pytest.mark.asyncio
    async def test_retrieve_with_expansion_with_group_filter(self, retriever, adapter):
        """测试带群聊过滤的路径扩展"""
        # 添加带群聊 ID 的节点
        node1 = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="软件工程师",
            group_id="group_123"
        )
        node1.id = node1.generate_id()
        
        node2 = GraphNode(
            id="",
            label="Person",
            name="Bob",
            content="数据科学家",
            group_id="group_456"  # 不同群聊
        )
        node2.id = node2.generate_id()
        
        await adapter.add_node(node1)
        await adapter.add_node(node2)
        
        # 执行检索（带群聊过滤）
        nodes, _ = await retriever.retrieve_with_expansion(
            [node1.id],
            group_id="group_123"
        )
        
        # 验证结果
        assert len(nodes) >= 1
    
    @pytest.mark.asyncio
    async def test_retrieve_with_expansion_timeout(self, retriever):
        """测试超时保护"""
        # 创建一个会超时的 mock adapter
        mock_adapter = MagicMock()
        mock_adapter._is_available = True
        
        # 模拟超时的 expand_from_nodes
        async def slow_expand(*args, **kwargs):
            await asyncio.sleep(10)  # 超长延迟
            return [], []
        
        mock_adapter.expand_from_nodes = slow_expand
        
        # 修改配置，设置很短的超时
        retriever.adapter = mock_adapter
        retriever.config._hidden_config.data["l3_kg.timeout_ms"] = 100  # 100ms
        
        # 执行检索
        nodes, edges = await retriever.retrieve_with_expansion(["test_id"])
        
        # 应该因为超时返回空结果
        assert nodes == []
        assert edges == []
    
    @pytest.mark.asyncio
    async def test_update_access_count(self, retriever, adapter):
        """测试更新访问计数"""
        # 添加测试节点
        node = GraphNode(
            id="",
            label="Person",
            name="Alice",
            content="软件工程师"
        )
        node.id = node.generate_id()
        
        await adapter.add_node(node)
        
        # 更新访问计数
        await retriever.update_access_count([node.id])
        
        # 验证更新（通过查询验证）
        # 注意：这需要 adapter 实现查询功能
        # 这里只验证不抛出异常
    
    @pytest.mark.asyncio
    async def test_update_access_count_empty_list(self, retriever):
        """测试空列表的访问计数更新"""
        # 不应该抛出异常
        await retriever.update_access_count([])
    
    @pytest.mark.asyncio
    async def test_update_access_count_adapter_unavailable(self, retriever):
        """测试适配器不可用时的访问计数更新"""
        # 设置适配器不可用
        retriever.adapter._is_available = False
        
        # 不应该抛出异常
        await retriever.update_access_count(["test_id"])
        
        # 恢复
        retriever.adapter._is_available = True
    
    @pytest.mark.asyncio
    async def test_retrieve_with_unavailable_adapter(self, retriever):
        """测试适配器不可用时的检索"""
        # 设置适配器不可用
        retriever.adapter._is_available = False
        
        # 执行检索
        nodes, edges = await retriever.retrieve_with_expansion(["test_id"])
        
        # 应该返回空结果
        assert nodes == []
        assert edges == []
        
        # 恢复
        retriever.adapter._is_available = True
