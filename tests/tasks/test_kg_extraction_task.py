"""
KGExtractionTask L3 知识图谱提取任务测试

测试知识图谱提取任务的核心功能：
- 阈值检测
- 未处理记忆获取
- 实体提取
- 记忆标记
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from iris_memory.tasks.kg_extraction_task import KGExtractionTask
from iris_memory.l2_memory.models import MemoryEntry
from iris_memory.l3_kg.models import GraphNode, GraphEdge, ExtractionResult


class TestKGExtractionTask:
    """KGExtractionTask 测试类"""
    
    @pytest.fixture
    def mock_component_manager(self):
        """创建模拟组件管理器"""
        manager = Mock()
        
        l2_adapter = Mock()
        l2_adapter.is_available = True
        l2_adapter.get_unprocessed_count = AsyncMock(return_value=0)
        l2_adapter.get_unprocessed_memories = AsyncMock(return_value=[])
        l2_adapter.mark_memories_processed = AsyncMock(return_value=True)
        
        l3_adapter = Mock()
        l3_adapter.is_available = True
        l3_adapter.add_node = AsyncMock(return_value=True)
        l3_adapter.add_edge = AsyncMock(return_value=True)
        
        llm_manager = Mock()
        llm_manager.is_available = True
        llm_manager.generate = AsyncMock(return_value='{"nodes": [], "edges": [], "extraction_confidence": 0.8}')
        
        def get_component(name):
            if name == "l2_memory":
                return l2_adapter
            elif name == "l3_kg":
                return l3_adapter
            elif name == "llm_manager":
                return llm_manager
            return None
        
        manager.get_component = get_component
        
        return manager
    
    @pytest.fixture
    def kg_extraction_task(self, mock_component_manager):
        """创建 KGExtractionTask 实例"""
        return KGExtractionTask(mock_component_manager)
    
    @pytest.mark.asyncio
    async def test_execute_l3_disabled(self, kg_extraction_task):
        """测试 L3 未启用时跳过"""
        with patch('iris_memory.tasks.kg_extraction_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "l3_kg.enable": False,
            }.get(key, None)
            
            await kg_extraction_task.execute()
            
            l2_adapter = kg_extraction_task._component_manager.get_component("l2_memory")
            l2_adapter.get_unprocessed_count.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_below_threshold(self, kg_extraction_task):
        """测试未处理记忆数量低于阈值时跳过"""
        with patch('iris_memory.tasks.kg_extraction_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "l3_kg.enable": True,
                "kg_extraction_min_unprocessed": 10,
                "kg_extraction_batch_size": 20,
                "kg_extraction_max_related": 5,
            }.get(key, None)
            
            await kg_extraction_task.execute()
            
            l2_adapter = kg_extraction_task._component_manager.get_component("l2_memory")
            l2_adapter.get_unprocessed_count.assert_called_once()
            l2_adapter.get_unprocessed_memories.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_above_threshold(self, kg_extraction_task):
        """测试未处理记忆数量达到阈值时执行提取"""
        unprocessed_memories = [
            MemoryEntry(
                id="mem_1",
                content="张三喜欢吃苹果",
                metadata={
                    "group_id": "group_123",
                    "user_id": "user_001",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        ]
        
        l2_adapter = kg_extraction_task._component_manager.get_component("l2_memory")
        l2_adapter.get_unprocessed_count = AsyncMock(return_value=15)
        l2_adapter.get_unprocessed_memories = AsyncMock(return_value=unprocessed_memories)
        
        llm_response = '''{
            "nodes": [
                {"label": "Person", "name": "张三", "content": "用户张三", "confidence": 0.9},
                {"label": "Item", "name": "苹果", "content": "水果苹果", "confidence": 0.8}
            ],
            "edges": [
                {"source_name": "张三", "target_name": "苹果", "relation_type": "LIKES", "confidence": 0.85}
            ],
            "extraction_confidence": 0.85
        }'''
        
        llm_manager = kg_extraction_task._component_manager.get_component("llm_manager")
        llm_manager.generate = AsyncMock(return_value=llm_response)
        
        with patch('iris_memory.tasks.kg_extraction_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "l3_kg.enable": True,
                "kg_extraction_min_unprocessed": 10,
                "kg_extraction_batch_size": 20,
                "kg_extraction_max_related": 5,
                "l3_kg.enable_type_whitelist": True,
            }.get(key, None)
            
            await kg_extraction_task.execute()
            
            l2_adapter.get_unprocessed_memories.assert_called_once()
            l2_adapter.mark_memories_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_l2_unavailable(self, kg_extraction_task):
        """测试 L2 不可用时跳过"""
        l2_adapter = kg_extraction_task._component_manager.get_component("l2_memory")
        l2_adapter.is_available = False
        
        with patch('iris_memory.tasks.kg_extraction_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "l3_kg.enable": True,
            }.get(key, None)
            
            await kg_extraction_task.execute()
            
            l2_adapter.get_unprocessed_count.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_llm_unavailable(self, kg_extraction_task):
        """测试 LLM 不可用时跳过"""
        llm_manager = kg_extraction_task._component_manager.get_component("llm_manager")
        llm_manager.is_available = False
        
        with patch('iris_memory.tasks.kg_extraction_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "l3_kg.enable": True,
                "kg_extraction_min_unprocessed": 10,
            }.get(key, None)
            
            await kg_extraction_task.execute()
            
            l2_adapter = kg_extraction_task._component_manager.get_component("l2_memory")
            l2_adapter.get_unprocessed_memories.assert_not_called()
