"""
Token 统计管理器测试
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from iris_memory.llm.token_stats import TokenUsage, TokenStatsManager


class TestTokenUsage:
    """TokenUsage 数据类测试"""
    
    def test_init_default_values(self):
        """测试默认值初始化"""
        usage = TokenUsage()
        assert usage.total_input_tokens == 0
        assert usage.total_output_tokens == 0
        assert usage.total_calls == 0
    
    def test_total_tokens_property(self):
        """测试 total_tokens 属性"""
        usage = TokenUsage(
            total_input_tokens=100,
            total_output_tokens=50,
            total_calls=1
        )
        assert usage.total_tokens == 150
    
    def test_to_dict(self):
        """测试转换为字典"""
        usage = TokenUsage(
            total_input_tokens=100,
            total_output_tokens=50,
            total_calls=1
        )
        data = usage.to_dict()
        assert data == {
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_calls": 1
        }
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_calls": 1
        }
        usage = TokenUsage.from_dict(data)
        assert usage.total_input_tokens == 100
        assert usage.total_output_tokens == 50
        assert usage.total_calls == 1
    
    def test_from_dict_partial(self):
        """测试从部分字典创建"""
        data = {"total_input_tokens": 100}
        usage = TokenUsage.from_dict(data)
        assert usage.total_input_tokens == 100
        assert usage.total_output_tokens == 0
        assert usage.total_calls == 0


class TestTokenStatsManager:
    """TokenStatsManager 测试"""
    
    @pytest.fixture
    def mock_context(self):
        """创建 mock Context"""
        context = MagicMock()
        context.get_kv_data = AsyncMock(return_value={})
        context.put_kv_data = AsyncMock()
        return context
    
    @pytest.fixture
    def manager(self, mock_context):
        """创建 TokenStatsManager 实例"""
        return TokenStatsManager(mock_context)
    
    @pytest.mark.asyncio
    async def test_init(self, manager):
        """测试初始化"""
        assert manager._context is not None
        assert manager._cache is not None
    
    @pytest.mark.asyncio
    async def test_record_usage_module(self, manager):
        """测试记录模块级 Token 使用"""
        await manager.record_usage("l1_summarizer", 100, 50)
        
        # 验证模块统计
        module_stats = manager._cache["l1_summarizer"]
        assert module_stats.total_input_tokens == 100
        assert module_stats.total_output_tokens == 50
        assert module_stats.total_calls == 1
        
        # 验证全局统计
        global_stats = manager._cache["global"]
        assert global_stats.total_input_tokens == 100
        assert global_stats.total_output_tokens == 50
        assert global_stats.total_calls == 1
    
    @pytest.mark.asyncio
    async def test_record_usage_multiple_times(self, manager):
        """测试多次记录 Token 使用"""
        await manager.record_usage("l1_summarizer", 100, 50)
        await manager.record_usage("l1_summarizer", 200, 100)
        
        module_stats = manager._cache["l1_summarizer"]
        assert module_stats.total_input_tokens == 300
        assert module_stats.total_output_tokens == 150
        assert module_stats.total_calls == 2
    
    @pytest.mark.asyncio
    async def test_record_usage_different_modules(self, manager):
        """测试不同模块的记录"""
        await manager.record_usage("l1_summarizer", 100, 50)
        await manager.record_usage("l3_kg_extraction", 200, 100)
        
        # 验证各模块统计
        l1_stats = manager._cache["l1_summarizer"]
        assert l1_stats.total_tokens == 150
        
        l3_stats = manager._cache["l3_kg_extraction"]
        assert l3_stats.total_tokens == 300
        
        # 验证全局统计
        global_stats = manager._cache["global"]
        assert global_stats.total_tokens == 450
        assert global_stats.total_calls == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """测试获取统计"""
        await manager.record_usage("l1_summarizer", 100, 50)
        
        stats = await manager.get_stats("l1_summarizer")
        assert stats.total_input_tokens == 100
        assert stats.total_output_tokens == 50
        assert stats.total_calls == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_global(self, manager):
        """测试获取全局统计"""
        await manager.record_usage("l1_summarizer", 100, 50)
        
        stats = await manager.get_stats("global")
        assert stats.total_tokens == 150
    
    @pytest.mark.asyncio
    async def test_reset_stats(self, manager):
        """测试重置统计"""
        await manager.record_usage("l1_summarizer", 100, 50)
        
        await manager.reset_stats("l1_summarizer")
        
        stats = await manager.get_stats("l1_summarizer")
        assert stats.total_tokens == 0
        assert stats.total_calls == 0
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self, manager):
        """测试获取所有统计"""
        await manager.record_usage("l1_summarizer", 100, 50)
        await manager.record_usage("l3_kg_extraction", 200, 100)
        
        all_stats = await manager.get_all_stats()
        
        assert "l1_summarizer" in all_stats
        assert "l3_kg_extraction" in all_stats
        assert "global" in all_stats
    
    @pytest.mark.asyncio
    async def test_kv_storage_persistence(self, manager, mock_context):
        """测试 KV 存储持久化"""
        await manager.record_usage("l1_summarizer", 100, 50)
        
        # 验证 put_kv_data 被调用
        assert mock_context.put_kv_data.called
        
        # 验证键名格式
        call_args = mock_context.put_kv_data.call_args
        key = call_args[0][0]
        assert key == "token_stats:module:l1_summarizer"
