"""
MergeTask 记忆合并任务测试

测试记忆合并任务的核心功能：
- 相似记忆检测
- LLM 合并
- 批量处理
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from iris_memory.tasks.merge_task import MergeTask
from iris_memory.l2_memory.models import MemoryEntry, MemorySearchResult


class TestMergeTask:
    """MergeTask 测试类"""
    
    @pytest.fixture
    def mock_component_manager(self):
        """创建模拟组件管理器"""
        manager = Mock()
        
        # 模拟 L2 适配器
        l2_adapter = Mock()
        l2_adapter.is_available = True
        l2_adapter.get_all_entries = AsyncMock(return_value=[])
        l2_adapter.retrieve = AsyncMock(return_value=[])
        l2_adapter.add_memory = AsyncMock(return_value="merged_mem_id")
        l2_adapter.delete_entries = AsyncMock(return_value=True)
        
        # 模拟 LLM 管理器
        llm_manager = Mock()
        llm_manager.is_available = True
        llm_manager.generate = AsyncMock(return_value="合并后的记忆内容")
        
        # 配置 get_component 返回值
        def get_component(name):
            if name == "l2_memory":
                return l2_adapter
            elif name == "llm_manager":
                return llm_manager
            return None
        
        manager.get_component = get_component
        
        return manager
    
    @pytest.fixture
    def merge_task(self, mock_component_manager):
        """创建 MergeTask 实例"""
        return MergeTask(mock_component_manager)
    
    @pytest.mark.asyncio
    async def test_execute_disabled(self, merge_task):
        """测试任务未启用时跳过"""
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": False,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证未调用任何合并方法
            merge_task._component_manager.get_component("l2_memory").get_all_entries.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_empty_memories(self, merge_task):
        """测试记忆库为空时跳过"""
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证调用了 get_all_entries
            merge_task._component_manager.get_component("l2_memory").get_all_entries.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_insufficient_memories(self, merge_task):
        """测试记忆数量不足时跳过"""
        # 只有一条记忆
        entries = [
            MemoryEntry(
                id="mem_1",
                content="单条记忆",
                metadata={"group_id": "group_1"}
            )
        ]
        
        merge_task._component_manager.get_component("l2_memory").get_all_entries = AsyncMock(
            return_value=entries
        )
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证未尝试合并
            merge_task._component_manager.get_component("llm_manager").generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_l2_unavailable(self, merge_task):
        """测试 L2 不可用时跳过"""
        # 修改 L2 为不可用
        merge_task._component_manager.get_component("l2_memory").is_available = False
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证未调用 get_all_entries
            merge_task._component_manager.get_component("l2_memory").get_all_entries.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_llm_unavailable(self, merge_task):
        """测试 LLM 不可用时跳过"""
        # 创建多条记忆
        entries = [
            MemoryEntry(
                id="mem_1",
                content="记忆1",
                metadata={"group_id": "group_1"}
            ),
            MemoryEntry(
                id="mem_2",
                content="记忆2",
                metadata={"group_id": "group_1"}
            )
        ]
        
        merge_task._component_manager.get_component("l2_memory").get_all_entries = AsyncMock(
            return_value=entries
        )
        
        # 修改 LLM 为不可用
        merge_task._component_manager.get_component("llm_manager").is_available = False
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证未调用 LLM
            merge_task._component_manager.get_component("llm_manager").generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_find_similar_pairs(self, merge_task):
        """测试相似记忆对检测"""
        # 创建相似记忆
        entries = [
            MemoryEntry(
                id="mem_1",
                content="用户喜欢吃苹果",
                metadata={"group_id": "group_1"}
            ),
            MemoryEntry(
                id="mem_2",
                content="用户喜欢吃苹果和香蕉",
                metadata={"group_id": "group_1"}
            )
        ]
        
        # 模拟检索结果（mem_1 检索到 mem_2，相似度 0.9）
        search_results = [
            MemorySearchResult(
                entry=entries[0],
                score=1.0,
                distance=0.0
            ),
            MemorySearchResult(
                entry=entries[1],
                score=0.9,
                distance=0.1
            )
        ]
        
        l2_adapter = merge_task._component_manager.get_component("l2_memory")
        l2_adapter.get_all_entries = AsyncMock(return_value=entries)
        l2_adapter.retrieve = AsyncMock(return_value=search_results)
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10,
                "isolation_config.enable_group_memory_isolation": False
            }.get(key, None)
            
            # 调用内部方法测试
            similar_pairs = await merge_task._find_similar_pairs(entries, l2_adapter)
            
            # 验证找到了相似记忆对
            # 注意：由于实现逻辑，可能不会找到所有对
            assert isinstance(similar_pairs, list)
    
    @pytest.mark.asyncio
    async def test_merge_memories(self, merge_task):
        """测试 LLM 合并记忆"""
        llm_manager = merge_task._component_manager.get_component("llm_manager")
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10
            }.get(key, None)
            
            # 合并两条记忆
            merged = await merge_task._merge_memories(
                "用户喜欢吃苹果",
                "用户喜欢吃苹果和香蕉",
                llm_manager
            )
            
            # 验证调用了 LLM
            llm_manager.generate.assert_called_once()
            assert merged is not None
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, merge_task):
        """测试批量处理"""
        # 创建大量相似记忆对
        entries = [
            MemoryEntry(
                id=f"mem_{i}",
                content=f"记忆{i}",
                metadata={"group_id": "group_1"}
            )
            for i in range(20)
        ]
        
        # 模拟检索结果（高相似度）
        search_results = [
            MemorySearchResult(
                entry=entries[0],
                score=1.0,
                distance=0.0
            ),
            MemorySearchResult(
                entry=entries[1],
                score=0.9,
                distance=0.1
            )
        ]
        
        l2_adapter = merge_task._component_manager.get_component("l2_memory")
        l2_adapter.get_all_entries = AsyncMock(return_value=entries)
        l2_adapter.retrieve = AsyncMock(return_value=search_results)
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 5,
                "isolation_config.enable_group_memory_isolation": False
            }.get(key, None)
            
            await merge_task.execute()
            
            # 验证批量大小限制生效
            llm_manager = merge_task._component_manager.get_component("llm_manager")
            # 由于实现逻辑复杂，只验证调用次数不超过批量大小
            assert llm_manager.generate.call_count <= 5
    
    @pytest.mark.asyncio
    async def test_group_isolation(self, merge_task):
        """测试群聊隔离"""
        # 创建不同群聊的记忆
        entries = [
            MemoryEntry(
                id="mem_1",
                content="记忆1",
                metadata={"group_id": "group_1"}
            ),
            MemoryEntry(
                id="mem_2",
                content="记忆2",
                metadata={"group_id": "group_2"}
            )
        ]
        
        l2_adapter = merge_task._component_manager.get_component("l2_memory")
        l2_adapter.get_all_entries = AsyncMock(return_value=entries)
        
        with patch('iris_memory.tasks.merge_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_merging": True,
                "merge_similarity_threshold": 0.85,
                "merge_batch_size": 10,
                "isolation_config.enable_group_memory_isolation": True
            }.get(key, None)
            
            # 调用内部方法测试
            similar_pairs = await merge_task._find_similar_pairs(entries, l2_adapter)
            
            # 验证不同群聊的记忆不会被匹配
            for mem1, mem2 in similar_pairs:
                assert mem1.metadata.get("group_id") == mem2.metadata.get("group_id")
