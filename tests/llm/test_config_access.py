"""LLM 配置访问测试

验证修复的问题：
- 隐藏配置键访问（移除 "hidden." 前缀）
"""

import pytest
from unittest.mock import MagicMock, patch

from iris_memory.llm.manager import LLMManager


class TestLLMConfigAccess:
    """LLM 配置访问测试"""
    
    @pytest.fixture
    def mock_context(self):
        """创建 mock Context"""
        context = MagicMock()
        
        # Mock llm_generate
        mock_response = MagicMock()
        mock_response.completion_text = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        context.llm_generate = MagicMock(return_value=mock_response)
        
        # Mock KV storage
        context.get_kv_data = MagicMock(return_value={})
        context.put_kv_data = MagicMock()
        
        return context
    
    @pytest.mark.asyncio
    async def test_hidden_config_access_without_prefix(self, mock_context):
        """测试隐藏配置访问（不带 hidden. 前缀）
        
        验证修复：配置键应该是 "call_log_max_entries" 而不是 "hidden.call_log_max_entries"
        """
        with patch('iris_memory.llm.manager.get_config') as mock_get_config:
            # 创建 mock 配置
            config = MagicMock()
            
            # 设置配置返回值
            def config_get(key, default=None):
                # 关键验证：应该使用 "call_log_max_entries" 而不是 "hidden.call_log_max_entries"
                if key == "call_log_max_entries":
                    return 200  # 自定义值
                return default
            
            config.get = MagicMock(side_effect=config_get)
            mock_get_config.return_value = config
            
            # 初始化 LLMManager
            manager = LLMManager(mock_context)
            await manager.initialize()
            
            # 验证配置被正确读取
            # 如果配置键错误，maxlen 会是默认值 100 而不是 200
            assert manager._call_logs.maxlen == 200
            
            # 验证配置访问使用了正确的键
            config.get.assert_called()
            called_keys = [call[0][0] for call in config.get.call_args_list]
            assert "call_log_max_entries" in called_keys
            assert "hidden.call_log_max_entries" not in called_keys
    
    @pytest.mark.asyncio
    async def test_default_value_when_config_missing(self, mock_context):
        """测试配置缺失时使用默认值"""
        with patch('iris_memory.llm.manager.get_config') as mock_get_config:
            config = MagicMock()
            
            # 模拟配置不存在
            config.get = MagicMock(return_value=None)
            mock_get_config.return_value = config
            
            manager = LLMManager(mock_context)
            await manager.initialize()
            
            # 应该使用默认值 100
            assert manager._call_logs.maxlen == 100
    
    @pytest.mark.asyncio
    async def test_config_access_with_custom_limit(self, mock_context):
        """测试自定义调用日志限制"""
        with patch('iris_memory.llm.manager.get_config') as mock_get_config:
            config = MagicMock()
            
            def config_get(key, default=None):
                if key == "call_log_max_entries":
                    return 500  # 大量日志
                return default
            
            config.get = MagicMock(side_effect=config_get)
            mock_get_config.return_value = config
            
            manager = LLMManager(mock_context)
            await manager.initialize()
            
            # 验证自定义限制生效
            assert manager._call_logs.maxlen == 500
            
            # 添加超过默认限制（100）的日志
            for i in range(150):
                manager._call_logs.append({"test": i})
            
            # 应该能容纳超过 100 条
            assert len(manager._call_logs) == 150
