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
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = True
        
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
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        buffer.get_context.assert_called_once_with("group123", 20)
        
        assert len(req.contexts) == 2
        assert req.contexts[0]["role"] == "user"
        assert req.contexts[0]["content"] == "你好"
    
    @pytest.mark.asyncio
    async def test_preprocess_with_unavailable_buffer(self):
        """测试 L1 Buffer 不可用时的对话前处理"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = False
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
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
        buffer.get_context.return_value = []
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
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
        
        assert len(req.contexts) == 2
        assert req.contexts[0]["role"] == "user"
        assert req.contexts[1]["role"] == "system"
    
    @pytest.mark.asyncio
    async def test_preprocess_with_user_name_binding(self):
        """测试用户消息绑定用户名"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = True
        
        from iris_memory.l1_buffer import ContextMessage
        messages = [
            ContextMessage(
                role="user", 
                content="你好", 
                timestamp=datetime.now(),
                token_count=2, 
                source="user1",
                metadata={"user_name": "张三"}
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
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        assert len(req.contexts) == 2
        assert req.contexts[0]["role"] == "user"
        assert req.contexts[0]["content"] == "[张三]: 你好"
        assert req.contexts[1]["role"] == "assistant"
        assert req.contexts[1]["content"] == "你好！"
    
    @pytest.mark.asyncio
    async def test_preprocess_without_user_name(self):
        """测试没有用户名时不绑定"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = True
        
        from iris_memory.l1_buffer import ContextMessage
        messages = [
            ContextMessage(
                role="user", 
                content="你好", 
                timestamp=datetime.now(),
                token_count=2, 
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
        
        assert len(req.contexts) == 1
        assert req.contexts[0]["content"] == "你好"
    
    @pytest.mark.asyncio
    async def test_preprocess_assistant_message_no_user_name(self):
        """测试助手消息不绑定用户名"""
        event = MagicMock()
        req = MagicMock()
        req.contexts = []
        
        buffer = MagicMock()
        buffer.is_available = True
        
        from iris_memory.l1_buffer import ContextMessage
        messages = [
            ContextMessage(
                role="assistant", 
                content="你好！", 
                timestamp=datetime.now(),
                token_count=3, 
                source="assistant",
                metadata={"user_name": "助手"}
            )
        ]
        buffer.get_context.return_value = messages
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        
        with patch('iris_memory.core.llm_request_hook.get_adapter', return_value=adapter):
            await preprocess_llm_request(event, req, component_manager)
        
        assert len(req.contexts) == 1
        assert req.contexts[0]["content"] == "你好！"
