"""平台适配器测试"""

import pytest
from unittest.mock import Mock
from iris_memory.platform.base import PlatformAdapter, UnsupportedPlatformError
from iris_memory.platform.factory import get_adapter
from iris_memory.platform.qq import OneBot11Adapter


class TestUnsupportedPlatformError:
    """UnsupportedPlatformError 测试"""
    
    def test_error_message(self):
        """测试错误消息"""
        error = UnsupportedPlatformError("wechat", "当前仅支持 QQ 平台")
        
        assert error.platform_type == "wechat"
        assert error.message == "当前仅支持 QQ 平台"
        assert str(error) == "当前仅支持 QQ 平台"
    
    def test_default_message(self):
        """测试默认消息"""
        error = UnsupportedPlatformError("wechat")
        
        assert error.platform_type == "wechat"
        assert "wechat" in error.message


class TestOneBot11Adapter:
    """OneBot11Adapter 测试"""
    
    def test_get_user_id(self):
        """测试获取用户ID"""
        adapter = OneBot11Adapter()
        
        event = Mock()
        event.sender = Mock()
        event.sender.user_id = "12345"
        
        user_id = adapter.get_user_id(event)
        
        assert user_id == "12345"
    
    def test_get_group_id(self):
        """测试获取群ID"""
        adapter = OneBot11Adapter()
        
        event = Mock()
        event.group_id = "group_123"
        event.sender = Mock()
        
        group_id = adapter.get_group_id(event)
        
        assert group_id == "group_123"
    
    def test_get_username(self):
        """测试获取用户名"""
        adapter = OneBot11Adapter()
        
        event = Mock()
        event.group_id = ""
        event.sender = Mock()
        event.sender.nickname = "测试用户"
        
        username = adapter.get_user_name(event)
        
        assert username == "测试用户"
    
    def test_is_group_message_true(self):
        """测试群聊判断 - 群聊"""
        adapter = OneBot11Adapter()
        
        event = Mock()
        event.group_id = "group_123"
        event.sender = Mock()
        
        assert adapter.is_group_message(event) == True
    
    def test_is_group_message_false(self):
        """测试群聊判断 - 私聊"""
        adapter = OneBot11Adapter()
        
        event = Mock()
        event.group_id = ""
        event.sender = Mock()
        
        assert adapter.is_group_message(event) == False


class TestGetAdapter:
    """get_adapter 工厂方法测试"""
    
    def test_get_onebot11_adapter_via_session(self):
        """测试获取 OneBot11 适配器 - 通过 session.platform_name"""
        event = Mock()
        event.session = Mock()
        event.session.platform_name = "aiocqhttp"
        
        adapter = get_adapter(event)
        
        assert isinstance(adapter, OneBot11Adapter)
    
    def test_get_onebot11_adapter_via_platform_adapter_type(self):
        """测试获取 OneBot11 适配器 - 通过 platform_adapter_type（旧版本兼容）"""
        event = Mock()
        event.session = None
        event.platform_meta = None
        event.platform_adapter = None
        event.platform_adapter_type = "aiocqhttp"
        
        adapter = get_adapter(event)
        
        assert isinstance(adapter, OneBot11Adapter)
    
    def test_get_unsupported_adapter(self):
        """测试获取不支持的适配器"""
        event = Mock()
        event.session = Mock()
        event.session.platform_name = "unsupported_platform"
        
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            get_adapter(event)
        
        assert exc_info.value.platform_type == "unsupported_platform"
    
    def test_adapter_is_singleton(self):
        """测试适配器是单例"""
        event1 = Mock()
        event1.session = Mock()
        event1.session.platform_name = "aiocqhttp"
        
        event2 = Mock()
        event2.session = Mock()
        event2.session.platform_name = "aiocqhttp"
        
        adapter1 = get_adapter(event1)
        adapter2 = get_adapter(event2)
        
        # 适配器应该是同一个实例（单例模式）
        assert adapter1 is adapter2
