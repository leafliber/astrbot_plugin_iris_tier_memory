"""
ForgettingTask 遗忘清洗任务测试

测试遗忘清洗任务的核心功能：
- L2 记忆遗忘清洗
- L3 图谱节点淘汰
- 批量处理
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from iris_memory.tasks.forgetting_task import ForgettingTask
from iris_memory.l2_memory.models import MemoryEntry


class TestForgettingTask:
    """ForgettingTask 测试类"""
    
    @pytest.fixture
    def mock_component_manager(self):
        """创建模拟组件管理器"""
        manager = Mock()
        
        # 模拟 L2 适配器
        l2_adapter = Mock()
        l2_adapter.is_available = True
        l2_adapter.get_all_entries = AsyncMock(return_value=[])
        l2_adapter.evict_memories = AsyncMock(return_value=0)
        
        # 模拟 L3 适配器
        l3_adapter = Mock()
        l3_adapter.is_available = True
        l3_adapter.get_all_nodes = AsyncMock(return_value=[])
        l3_adapter.evict_nodes = AsyncMock(return_value=0)
        
        # 配置 get_component 返回值
        def get_component(name):
            if name == "l2_memory":
                return l2_adapter
            elif name == "l3_kg":
                return l3_adapter
            return None
        
        manager.get_component = get_component
        
        return manager
    
    @pytest.fixture
    def forgetting_task(self, mock_component_manager):
        """创建 ForgettingTask 实例"""
        return ForgettingTask(mock_component_manager)
    
    @pytest.mark.asyncio
    async def test_execute_disabled(self, forgetting_task):
        """测试任务未启用时跳过"""
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": False,
                "eviction_batch_size": 100
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证未调用任何淘汰方法
            forgetting_task._component_manager.get_component("l2_memory").get_all_entries.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_l2_empty(self, forgetting_task):
        """测试 L2 为空时跳过"""
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 100,
                "forgetting_threshold": 0.3,
                "forgetting_lambda": 0.1
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证调用了 get_all_entries
            forgetting_task._component_manager.get_component("l2_memory").get_all_entries.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_l2_with_memories(self, forgetting_task):
        """测试 L2 有记忆时的清洗"""
        # 创建测试记忆
        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        recent_time = datetime.now().isoformat()
        
        entries = [
            MemoryEntry(
                id="mem_old_1",
                content="旧记忆1",
                metadata={
                    "last_access_time": old_time,
                    "access_count": 0,
                    "confidence": 0.1
                }
            ),
            MemoryEntry(
                id="mem_recent",
                content="近期记忆",
                metadata={
                    "last_access_time": recent_time,
                    "access_count": 10,
                    "confidence": 0.9
                }
            ),
            MemoryEntry(
                id="mem_old_2",
                content="旧记忆2",
                metadata={
                    "last_access_time": old_time,
                    "access_count": 0,
                    "confidence": 0.1
                }
            )
        ]
        
        forgetting_task._component_manager.get_component("l2_memory").get_all_entries = AsyncMock(
            return_value=entries
        )
        
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 100,
                "forgetting_threshold": 0.3,
                "forgetting_lambda": 0.1
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证调用了淘汰方法
            l2_adapter = forgetting_task._component_manager.get_component("l2_memory")
            l2_adapter.evict_memories.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_l3_empty(self, forgetting_task):
        """测试 L3 为空时跳过"""
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 100,
                "forgetting_threshold_kg": 0.2,
                "kg_retention_days": 30,
                "forgetting_lambda": 0.1
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证调用了 get_all_nodes
            forgetting_task._component_manager.get_component("l3_kg").get_all_nodes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_l2_unavailable(self, forgetting_task):
        """测试 L2 不可用时跳过"""
        # 修改 L2 为不可用
        forgetting_task._component_manager.get_component("l2_memory").is_available = False
        
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 100
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证未调用 get_all_entries
            forgetting_task._component_manager.get_component("l2_memory").get_all_entries.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_l3_unavailable(self, forgetting_task):
        """测试 L3 不可用时跳过"""
        # 修改 L3 为不可用
        forgetting_task._component_manager.get_component("l3_kg").is_available = False
        
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 100
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证未调用 get_all_nodes
            forgetting_task._component_manager.get_component("l3_kg").get_all_nodes.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, forgetting_task):
        """测试批量处理"""
        # 创建大量旧记忆
        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        entries = [
            MemoryEntry(
                id=f"mem_{i}",
                content=f"记忆{i}",
                metadata={
                    "last_access_time": old_time,
                    "access_count": 0,
                    "confidence": 0.1
                }
            )
            for i in range(150)
        ]
        
        forgetting_task._component_manager.get_component("l2_memory").get_all_entries = AsyncMock(
            return_value=entries
        )
        
        with patch('iris_memory.tasks.forgetting_task.get_config') as mock_config:
            mock_config.return_value.get.side_effect = lambda key: {
                "scheduled_tasks.enable_forgetting": True,
                "eviction_batch_size": 50,
                "forgetting_threshold": 0.3,
                "forgetting_lambda": 0.1
            }.get(key, None)
            
            await forgetting_task.execute()
            
            # 验证调用了多次 evict_memories（批量删除）
            l2_adapter = forgetting_task._component_manager.get_component("l2_memory")
            assert l2_adapter.evict_memories.call_count >= 2
