"""临时测试脚本"""
import sys
import os

# 切换到项目目录
os.chdir(r"c:\Users\leaf\code\astrbot_plugin_iris_tier_memory")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.getcwd())

import pytest

# 运行测试
sys.exit(pytest.main([
    '-v',
    'tests/image/',
    '--tb=short',
    '--capture=no'  # 显示所有输出
]))
