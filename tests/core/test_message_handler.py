"""测试消息处理模块"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from iris_memory.core.message_handler import handle_user_message, update_l1_buffer


class TestHandleUserMessage:
    """测试用户消息处理主函数"""
    
    @pytest.mark.asyncio
    async def test_handle_with_available_buffer(self):
        """测试 L1 Buffer 可用时的消息处理"""
        # 创建模拟对象
        event = MagicMock()
        event.message_str = "你好"
        
        # 模拟 L1Buffer 组件
        buffer = MagicMock()
        buffer.is_available = True
        buffer.add_message = AsyncMock()
        
        # 模拟组件管理器
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 模拟平台适配器
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        adapter.get_user_id.return_value = "user456"
        
        with patch('iris_memory.core.message_handler.get_adapter', return_value=adapter):
            await handle_user_message(event, component_manager)
        
        # 验证调用了 add_message
        buffer.add_message.assert_called_once_with(
            group_id="group123",
            role="user",
            content="你好",
            source="user456"
        )
    
    @pytest.mark.asyncio
    async def test_handle_with_unavailable_buffer(self):
        """测试 L1 Buffer 不可用时的消息处理"""
        event = MagicMock()
        event.message_str = "你好"
        
        # 模拟不可用的 L1Buffer
        buffer = MagicMock()
        buffer.is_available = False
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 不应该调用 add_message
        await handle_user_message(event, component_manager)
        
        buffer.add_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_with_empty_content(self):
        """测试消息内容为空时的处理"""
        event = MagicMock()
        event.message_str = ""  # 空消息
        
        buffer = MagicMock()
        buffer.is_available = True
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 不应该调用 add_message
        await handle_user_message(event, component_manager)
        
        buffer.add_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_with_none_content(self):
        """测试消息内容为 None 时的处理"""
        event = MagicMock()
        event.message_str = None
        
        buffer = MagicMock()
        buffer.is_available = True
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 不应该调用 add_message
        await handle_user_message(event, component_manager)
        
        buffer.add_message.assert_not_called()


class TestUpdateL1Buffer:
    """测试 L1 Buffer 更新函数"""
    
    @pytest.mark.asyncio
    async def test_update_with_user_message(self):
        """测试添加用户消息"""
        event = MagicMock()
        
        buffer = MagicMock()
        buffer.is_available = True
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        adapter.get_user_id.return_value = "user456"
        
        with patch('iris_memory.core.message_handler.get_adapter', return_value=adapter):
            await update_l1_buffer(event, component_manager, "user", "你好")
        
        # 验证调用了 add_message
        buffer.add_message.assert_called_once_with(
            group_id="group123",
            role="user",
            content="你好",
            source="user456"
        )
    
    @pytest.mark.asyncio
    async def test_update_with_assistant_message(self):
        """测试添加助手消息"""
        event = MagicMock()
        
        buffer = MagicMock()
        buffer.is_available = True
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        adapter = MagicMock()
        adapter.get_group_id.return_value = "group123"
        adapter.get_user_id.return_value = "user456"
        
        with patch('iris_memory.core.message_handler.get_adapter', return_value=adapter):
            await update_l1_buffer(event, component_manager, "assistant", "你好！")
        
        # 验证调用了 add_message
        buffer.add_message.assert_called_once_with(
            group_id="group123",
            role="assistant",
            content="你好！",
            source="assistant"
        )
    
    @pytest.mark.asyncio
    async def test_update_with_unavailable_buffer(self):
        """测试 L1 Buffer 不可用时不添加消息"""
        event = MagicMock()
        
        buffer = MagicMock()
        buffer.is_available = False
        buffer.add_message = AsyncMock()
        
        component_manager = MagicMock()
        component_manager.get_component.return_value = buffer
        
        # 不应该调用 add_message
        await update_l1_buffer(event, component_manager, "user", "你好")
        
        buffer.add_message.assert_not_called()
