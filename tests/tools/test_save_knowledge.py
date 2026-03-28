"""save_knowledge Tool 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from iris_memory.tools.save_knowledge import save_knowledge
from iris_memory.l3_kg import L3KGAdapter


class TestSaveKnowledgeTool:
    """save_knowledge Tool 测试"""
    
    @pytest.fixture
    def mock_adapter(self):
        """创建 mock 适配器"""
        adapter = MagicMock(spec=L3KGAdapter)
        adapter._is_available = True
        adapter.add_node = AsyncMock(return_value=True)
        adapter.add_edge = AsyncMock(return_value=True)
        return adapter
    
    @pytest.fixture
    def mock_component_manager(self, mock_adapter):
        """创建 mock 组件管理器"""
        manager = MagicMock()
        manager.get_component = MagicMock(return_value=mock_adapter)
        return manager
    
    @pytest.mark.asyncio
    async def test_save_knowledge_basic(self, mock_component_manager, monkeypatch):
        """测试基本保存功能"""
        # Mock get_component_manager
        monkeypatch.setattr(
            "iris_memory.tools.save_knowledge.get_component_manager",
            lambda: mock_component_manager
        )
        
        nodes = [
            {
                "label": "Person",
                "name": "Alice",
                "content": "Alice is a software engineer",
                "confidence": 0.9
            }
        ]
        
        edges = []
        
        result = await save_knowledge(nodes=nodes, edges=edges)
        
        assert "成功保存" in result
        assert "1 个节点" in result
    
    @pytest.mark.asyncio
    async def test_save_knowledge_with_edges(self, mock_component_manager, monkeypatch):
        """测试保存节点和边"""
        monkeypatch.setattr(
            "iris_memory.tools.save_knowledge.get_component_manager",
            lambda: mock_component_manager
        )
        
        nodes = [
            {
                "label": "Person",
                "name": "Alice",
                "content": "Alice is a software engineer",
                "confidence": 0.9
            },
            {
                "label": "Event",
                "name": "Conference",
                "content": "AI Conference 2024",
                "confidence": 0.8
            }
        ]
        
        edges = [
            {
                "source_name": "Alice",
                "target_name": "Conference",
                "relation_type": "ATTENDED",
                "confidence": 0.85
            }
        ]
        
        result = await save_knowledge(nodes=nodes, edges=edges)
        
        assert "成功保存" in result
        assert "2 个节点" in result
        assert "1 条边" in result
    
    @pytest.mark.asyncio
    async def test_save_knowledge_empty_nodes(self, mock_component_manager, monkeypatch):
        """测试空节点列表"""
        monkeypatch.setattr(
            "iris_memory.tools.save_knowledge.get_component_manager",
            lambda: mock_component_manager
        )
        
        result = await save_knowledge(nodes=[], edges=[])
        
        assert "未提供任何节点" in result
    
    @pytest.mark.asyncio
    async def test_save_knowledge_adapter_unavailable(self, monkeypatch):
        """测试适配器不可用"""
        mock_manager = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter._is_available = False
        mock_manager.get_component = MagicMock(return_value=mock_adapter)
        
        monkeypatch.setattr(
            "iris_memory.tools.save_knowledge.get_component_manager",
            lambda: mock_manager
        )
        
        result = await save_knowledge(
            nodes=[{"label": "Person", "name": "Alice", "content": "Test"}],
            edges=[]
        )
        
        assert "知识图谱不可用" in result
