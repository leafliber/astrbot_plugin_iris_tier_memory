"""
Iris Tier Memory - 核心模块

提供日志、组件管理等基础功能
"""

from .logger import get_logger
from .components import Component, ComponentManager, ComponentInitResult, SystemStatus

__all__ = [
    "get_logger",
    "Component",
    "ComponentManager",
    "ComponentInitResult",
    "SystemStatus",
]
