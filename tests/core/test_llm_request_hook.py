"""测试 LLM 请求钩子处理模块"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from iris_memory.core.llm_request_hook import preprocess_llm_request


class TestPreprocessLLMRequest:
    """测试 LLM 对话前处理主函数"""
    
    @pytest.mark.asyncio
    async def test_preprocess_with_available_buffer(self):
        """测试 L1 Buffer 可用时的对话前处理"""
        # 创建模拟对象
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        # 模拟 L1Buffer 组件
        buffer = MagicMock()
        buffer.is_available = True
        
        # 模拟消息
        from iris_memory.l1_buffer import ContextMessage
        messages = [
            ContextMessage(
                role="user", 
                content="你好", 
                timestamp=datetime.now(),
                token_count=2, 
                source="user1"
            ),
            ContextMessage(
                role="assistant", 
                content="你好！", 
                timestamp=datetime.now(),
                token_count=3, 
                source="assistant"
            )
        ]
        buffer.get_context.return_value = messages
        
        # 模拟组件管理器
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 模拟平台适配器
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        # 验证调用了 get_context
        buffer.get_context.assert_called_once_with("group123", 20)
        
        # 验证注入了上下文
        assert len(req.contexts) == 2
        assert req.contexts[0]["role"] == "user"
        assert req.contexts[0]["content"] == "你好"
    
    @pytest.mark.asyncio
    async def test_preprocess_with_unavailable_buffer(self):
        """测试 L1 Buffer 不可用时的对话前处理"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        # 模拟不可用的 L1Buffer
        buffer = MagicMock()
        buffer.is_available = False
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 不应该修改 req.contexts
        await preprocess_llm_request(event, req, component_manager)
        
        assert req.contexts == []
    
    @pytest.mark.asyncio
    async def test_preprocess_with_empty_messages(self):
        """测试 L1 Buffer 消息为空时的对话前处理"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = True
        buffer.get_context.return_value = []  # 空消息列表
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        # 不应该注入任何内容
        assert req.contexts == []
    
    @pytest.mark.asyncio
    async def test_preprocess_appends_to_existing_contexts(self):
        """测试已有上下文时注入 L1 消息"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = [{"role": "system", "content": "你是助手"}]
        
        buffer = MagicMock()
        buffer.is_available = True
        
        from iris_memory.l1_buffer import ContextMessage
        messages = [
            ContextMessage(
                role="user", 
                content="问题", 
                timestamp=datetime.now(),
                token_count=1, 
                source="user1"
            )
        ]
        buffer.get_context.return_value = messages
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        # 应该在开头插入 L1 消息
        assert len(req.contexts) == 2
        assert req.contexts[0]["role"] == "user"
        assert req.contexts[1]["role"] == "system"
