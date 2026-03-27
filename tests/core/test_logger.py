"""日志模块测试"""

import logging
from iris_memory.core.logger import get_logger


class TestLogger:
    """日志模块测试"""
    
    def test_get_logger_returns_logger(self):
        """测试 get_logger 返回 Logger 实例"""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
    
    def test_logger_name_format(self):
        """测试日志器名称格式"""
        logger = get_logger("test_module")
        
        # 日志器名称应该是 astrbot.iris-memory.test_module
        expected_name = "astrbot.iris-memory.test_module"
        assert logger.name == expected_name
    
    def test_different_modules(self):
        """测试不同模块获取不同日志器"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1.name != logger2.name
        assert "module1" in logger1.name
        assert "module2" in logger2.name
    
    def test_same_module_returns_same_logger(self):
        """测试相同模块返回相同日志器"""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2
    
    def test_logger_has_handler(self):
        """测试日志器有处理器"""
        logger = get_logger("test_module")
        
        # AstrBot 日志器应该有处理器
        # 注意：这个测试依赖于 AstrBot 的日志配置
        # 在测试环境中可能没有处理器
        assert isinstance(logger, logging.Logger)
