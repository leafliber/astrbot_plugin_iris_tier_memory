"""
测试图增强检索器
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from iris_memory.l2_memory.models import MemoryEntry, MemorySearchResult
from iris_memory.enhancement.graph_enhancement import GraphEnhancer


def create_memory_result(content: str, node_id: str = None) -> MemorySearchResult:
    """创建测试用的记忆检索结果"""
    metadata = {}
    if node_id:
        metadata["kg_node_id"] = node_id
    
    entry = MemoryEntry(
        id=f"mem_{hash(content)}",
        content=content,
        metadata=metadata
    )
    return MemorySearchResult(entry=entry, score=0.9, distance=0.1)


class TestGraphEnhancer:
    """图增强检索器测试"""
    
    @pytest.fixture
    def mock_component_manager(self):
        """创建模拟的组件管理器"""
        manager = MagicMock()
        
        # 模拟 L3 adapter
        l3_adapter = MagicMock()
        l3_adapter.is_available = True
        manager.get_component.return_value = l3_adapter
        
        return manager
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟的配置"""
        config = MagicMock()
        config.get = MagicMock(side_effect=lambda key, default=None: {
            "l2_memory.enable_graph_enhancement": True,
        }.get(key, default))
        return config
    
    @pytest.mark.asyncio
    async def test_enhance_disabled(self, mock_component_manager):
        """测试图增强未启用"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            memories = [create_memory_result("测试记忆")]
            enhanced, graph_context = await enhancer.enhance(memories)
            
            # 验证返回原始记忆
            assert enhanced == memories
            assert graph_context == ""
    
    @pytest.mark.asyncio
    async def test_enhance_no_node_ids(self, mock_component_manager):
        """测试记忆中没有节点 ID"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            # 模拟 L3 adapter 不可用
            mock_component_manager.get_component.return_value = None
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            # 创建没有节点 ID 的记忆
            memories = [create_memory_result("测试记忆", node_id=None)]
            enhanced, graph_context = await enhancer.enhance(memories)
            
            # 验证返回原始记忆
            assert enhanced == memories
            assert graph_context == ""
    
    @pytest.mark.asyncio
    async def test_enhance_with_valid_node_ids(self, mock_component_manager):
        """测试有效的图增强"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config, \
             patch('iris_memory.enhancement.graph_enhancement.GraphRetriever') as mock_retriever_class:
            
            mock_config = MagicMock()
            mock_config.get = MagicMock(side_effect=lambda key, default=None: {
                "l2_memory.enable_graph_enhancement": True,
            }.get(key, default))
            mock_get_config.return_value = mock_config
            
            # 模拟 GraphRetriever
            mock_retriever = MagicMock()
            mock_retriever.retrieve_with_expansion = AsyncMock(return_value=(
                [{"id": "node_1", "name": "实体1", "label": "Person", "content": "描述"}],
                [{"source": "node_1", "target": "node_2", "relation_type": "KNOWS"}]
            ))
            mock_retriever.format_for_context = MagicMock(return_value="## 知识图谱关联信息\n\n### Person\n- 实体1: 描述\n\n### 关系\n- 实体1 --[KNOWS]--> 实体2")
            mock_retriever.update_access_count = AsyncMock()
            mock_retriever_class.return_value = mock_retriever
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            # 创建带节点 ID 的记忆
            memories = [
                create_memory_result("测试记忆1", node_id="node_1"),
                create_memory_result("测试记忆2", node_id="node_2"),
            ]
            
            enhanced, graph_context = await enhancer.enhance(memories)
            
            # 验证图增强成功
            assert enhanced == memories
            assert "知识图谱关联信息" in graph_context
            
            # 验证调用了路径扩展
            mock_retriever.retrieve_with_expansion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enhance_exception_handling(self, mock_component_manager):
        """测试异常处理"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config, \
             patch('iris_memory.enhancement.graph_enhancement.GraphRetriever') as mock_retriever_class:
            
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            # 模拟 GraphRetriever 抛出异常
            mock_retriever = MagicMock()
            mock_retriever.retrieve_with_expansion = AsyncMock(side_effect=Exception("图谱检索失败"))
            mock_retriever_class.return_value = mock_retriever
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            memories = [create_memory_result("测试记忆", node_id="node_1")]
            enhanced, graph_context = await enhancer.enhance(memories)
            
            # 验证异常被捕获，返回原始记忆
            assert enhanced == memories
            assert graph_context == ""
    
    def test_extract_node_ids(self, mock_component_manager):
        """测试提取节点 ID"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            # 创建带不同字段名的记忆
            memories = [
                create_memory_result("记忆1"),
                MemorySearchResult(
                    entry=MemoryEntry(
                        id="mem_2",
                        content="记忆2",
                        metadata={"kg_node_id": "node_1"}
                    ),
                    score=0.9,
                    distance=0.1
                ),
                MemorySearchResult(
                    entry=MemoryEntry(
                        id="mem_3",
                        content="记忆3",
                        metadata={"node_id": "node_2"}
                    ),
                    score=0.9,
                    distance=0.1
                ),
                MemorySearchResult(
                    entry=MemoryEntry(
                        id="mem_4",
                        content="记忆4",
                        metadata={"entity_id": "node_3"}
                    ),
                    score=0.9,
                    distance=0.1
                ),
            ]
            
            node_ids = enhancer._extract_node_ids(memories)
            
            # 验证提取了所有节点 ID
            assert "node_1" in node_ids
            assert "node_2" in node_ids
            assert "node_3" in node_ids
            assert len(node_ids) == 3
    
    def test_extract_node_ids_deduplication(self, mock_component_manager):
        """测试节点 ID 去重"""
        with patch('iris_memory.enhancement.graph_enhancement.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            enhancer = GraphEnhancer(mock_component_manager)
            
            # 创建重复节点 ID 的记忆
            memories = [
                MemorySearchResult(
                    entry=MemoryEntry(
                        id="mem_1",
                        content="记忆1",
                        metadata={"kg_node_id": "node_1"}
                    ),
                    score=0.9,
                    distance=0.1
                ),
                MemorySearchResult(
                    entry=MemoryEntry(
                        id="mem_2",
                        content="记忆2",
                        metadata={"kg_node_id": "node_1"}
                    ),
                    score=0.9,
                    distance=0.1
                ),
            ]
            
            node_ids = enhancer._extract_node_ids(memories)
            
            # 验证节点 ID 已去重
            assert node_ids == ["node_1"]
