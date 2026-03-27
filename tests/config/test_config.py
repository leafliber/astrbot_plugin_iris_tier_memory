"""配置系统测试"""

import pytest
from pathlib import Path
from unittest.mock import Mock
from iris_memory.config import Config, init_config, get_config
from iris_memory.config.hidden_config import HiddenConfigManager


class TestConfig:
    """Config 类测试"""
    
    def test_get_flat_key(self, tmp_path: Path):
        """测试扁平化键名访问"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={"enable": True, "max_tokens": 1000})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {"test_key": "default_value"}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        # 测试用户配置访问
        assert config.get("l1_buffer.enable") == True
    
    def test_get_with_default(self, tmp_path: Path):
        """测试带默认值的访问"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        # 测试不存在的键返回默认值
        assert config.get("nonexistent", "default") == "default"
    
    def test_set_hidden_config(self, tmp_path: Path):
        """测试隐藏配置设置"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        # 设置隐藏配置
        config.set_hidden("debug_mode", True)
        
        # 读取隐藏配置
        assert config.get("debug_mode") == True
    
    def test_config_priority(self, tmp_path: Path):
        """测试配置优先级：用户配置 > 隐藏配置 > 默认值"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={"test_key": "user_value"})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {"test_key": "default_value"}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        # 用户配置优先
        assert config.get("test_key") == "user_value"
        
        # 设置隐藏配置后，用户配置仍然优先
        config.set_hidden("test_key", "hidden_value")
        assert config.get("test_key") == "user_value"
    
    def test_data_dir_property(self, tmp_path: Path):
        """测试 data_dir 属性"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        assert config.data_dir == tmp_path
    
    def test_on_config_change(self, tmp_path: Path):
        """测试配置变更监听"""
        astrbot_config = Mock()
        astrbot_config.__getitem__ = Mock(return_value={})
        astrbot_config.__contains__ = Mock(return_value=True)
        
        hidden_manager = HiddenConfigManager(tmp_path)
        defaults = {}
        
        config = Config(astrbot_config, hidden_manager, defaults, tmp_path)
        
        # 记录变更
        changes = []
        
        def on_change(key, old_value, new_value):
            changes.append((key, old_value, new_value))
        
        # 注册监听器
        config.on_config_change(on_change)
        
        # 修改隐藏配置
        config.set_hidden("debug_mode", True)
        
        # 验证监听器被调用
        assert len(changes) == 1
        assert changes[0] == ("debug_mode", None, True)


class TestHiddenConfigManager:
    """HiddenConfigManager 测试"""
    
    def test_get_set(self, tmp_path: Path):
        """测试获取和设置"""
        manager = HiddenConfigManager(tmp_path)
        
        # 设置值
        manager.set("test_key", "test_value")
        
        # 获取值
        assert manager.get("test_key") == "test_value"
    
    def test_persistence(self, tmp_path: Path):
        """测试持久化"""
        manager1 = HiddenConfigManager(tmp_path)
        manager1.set("test_key", "test_value")
        
        # 创建新实例，应该从文件加载
        manager2 = HiddenConfigManager(tmp_path)
        assert manager2.get("test_key") == "test_value"
    
    def test_default_value(self, tmp_path: Path):
        """测试默认值"""
        manager = HiddenConfigManager(tmp_path)
        
        # 不存在的键返回默认值
        assert manager.get("nonexistent", "default") == "default"


def test_global_config(tmp_path: Path):
    """测试全局配置访问"""
    # 初始化配置
    astrbot_config = Mock()
    astrbot_config.__getitem__ = Mock(return_value={"enable": True})
    astrbot_config.__contains__ = Mock(return_value=True)
    
    init_config(astrbot_config, tmp_path)
    
    # 通过全局函数访问
    config = get_config()
    assert config is not None
    assert config.data_dir == tmp_path
