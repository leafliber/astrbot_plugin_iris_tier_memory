"""
LLM 管理器测试
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from iris_memory.llm.manager import LLMManager
from iris_memory.llm.call_log import CallLog


class TestLLMManager:
    """LLMManager 测试"""
    
    @pytest.fixture
    def mock_context(self):
        """创建 mock Context"""
        context = MagicMock()
        
        # Mock llm_generate
        mock_response = MagicMock()
        mock_response.completion_text = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.input_other = 80
        mock_response.usage.input_cached = 20
        mock_response.usage.output_tokens = 50
        context.llm_generate = AsyncMock(return_value=mock_response)
        
        # Mock KV storage
        context.get_kv_data = AsyncMock(return_value={})
        context.put_kv_data = AsyncMock()
        
        return context
    
    @pytest.fixture
    def mock_config(self):
        """创建 mock Config"""
        with patch('iris_memory.llm.manager.get_config') as mock:
            config = MagicMock()
            config.get = MagicMock(return_value=100)
            mock.return_value = config
            yield config
    
    @pytest.mark.asyncio
    async def test_init(self, mock_context, mock_config):
        """测试初始化"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        assert manager.is_available is True
        assert manager._token_stats is not None
        assert manager._call_logs is not None
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_context, mock_config):
        """测试关闭"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        await manager.shutdown()
        
        assert manager.is_available is False
    
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_context, mock_config):
        """测试成功调用 generate"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        response = await manager.generate(
            prompt="Hello",
            module="l1_summarizer"
        )
        
        assert response == "Test response"
        assert mock_context.llm_generate.called
        
        # 验证调用日志
        logs = manager.get_recent_call_logs()
        assert len(logs) == 1
        assert logs[0]["success"] is True
        assert logs[0]["module"] == "l1_summarizer"
        assert logs[0]["input_tokens"] == 100
        assert logs[0]["output_tokens"] == 50
    
    @pytest.mark.asyncio
    async def test_generate_with_provider(self, mock_context, mock_config):
        """测试使用指定 Provider"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        response = await manager.generate(
            prompt="Hello",
            module="l1_summarizer",
            provider_id="gpt-4o"
        )
        
        # 验证 llm_generate 被调用时传入了正确的 provider_id
        call_args = mock_context.llm_generate.call_args
        assert call_args[1]["chat_provider_id"] == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_generate_failure(self, mock_context, mock_config):
        """测试调用失败"""
        # Mock llm_generate 抛出异常
        mock_context.llm_generate = AsyncMock(side_effect=Exception("API Error"))
        
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        with pytest.raises(Exception, match="API Error"):
            await manager.generate(
                prompt="Hello",
                module="l1_summarizer"
            )
        
        # 验证失败日志
        logs = manager.get_recent_call_logs()
        assert len(logs) == 1
        assert logs[0]["success"] is False
        assert "API Error" in logs[0]["error_message"]
    
    @pytest.mark.asyncio
    async def test_call_protocol(self, mock_context, mock_config):
        """测试 LLMCaller 协议接口"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        response = await manager.call("Hello", provider="gpt-4o")
        
        assert response == "Test response"
    
    @pytest.mark.asyncio
    async def test_get_token_stats(self, mock_context, mock_config):
        """测试获取 Token 统计"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        # 调用 generate 记录统计
        await manager.generate("Hello", module="l1_summarizer")
        
        stats = await manager.get_token_stats("l1_summarizer")
        
        assert stats["module"] == "l1_summarizer"
        assert stats["total_input_tokens"] == 100
        assert stats["total_output_tokens"] == 50
        assert stats["total_calls"] == 1
    
    @pytest.mark.asyncio
    async def test_get_all_token_stats(self, mock_context, mock_config):
        """测试获取所有 Token 统计"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        # 调用 generate 记录统计
        await manager.generate("Hello", module="l1_summarizer")
        await manager.generate("World", module="l3_kg_extraction")
        
        all_stats = await manager.get_all_token_stats()
        
        assert "l1_summarizer" in all_stats
        assert "l3_kg_extraction" in all_stats
        assert "global" in all_stats
    
    @pytest.mark.asyncio
    async def test_reset_token_stats(self, mock_context, mock_config):
        """测试重置 Token 统计"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        # 调用 generate 记录统计
        await manager.generate("Hello", module="l1_summarizer")
        
        # 重置统计
        await manager.reset_token_stats("l1_summarizer")
        
        stats = await manager.get_token_stats("l1_summarizer")
        assert stats["total_tokens"] == 0
    
    @pytest.mark.asyncio
    async def test_get_recent_call_logs(self, mock_context, mock_config):
        """测试获取最近调用日志"""
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        # 调用 generate 生成日志
        await manager.generate("Hello", module="l1_summarizer")
        await manager.generate("World", module="l3_kg_extraction")
        
        logs = manager.get_recent_call_logs(limit=10)
        
        assert len(logs) == 2
        assert logs[0]["module"] == "l1_summarizer"
        assert logs[1]["module"] == "l3_kg_extraction"
    
    @pytest.mark.asyncio
    async def test_provider_resolution_priority(self, mock_context, mock_config):
        """测试 Provider 解析优先级"""
        # Mock 配置返回特定 provider
        mock_config.get = MagicMock(return_value="gpt-4o-mini")
        
        manager = LLMManager(mock_context)
        await manager.initialize()
        
        # 测试参数优先级最高
        await manager.generate(
            prompt="Hello",
            module="l1_summarizer",
            provider_id="gpt-4o"
        )
        
        call_args = mock_context.llm_generate.call_args
        assert call_args[1]["chat_provider_id"] == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_not_initialized_error(self, mock_context, mock_config):
        """测试未初始化错误"""
        manager = LLMManager(mock_context)
        
        # 不初始化就调用
        with pytest.raises(RuntimeError, match="LLMManager 未初始化"):
            await manager.generate("Hello", module="test")
