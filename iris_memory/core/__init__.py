"""
Iris Tier Memory - 核心模块

提供日志、组件管理、LLM 对话前处理、消息处理、插件生命周期管理等基础功能
"""

from .logger import get_logger
from .components import Component, ComponentManager, ComponentInitResult, SystemStatus
from .llm_request_hook import preprocess_llm_request
from .message_hook import handle_user_message, update_l1_buffer
from .lifecycle import create_components, initialize_components, shutdown_components
from .llm_response_hook import handle_llm_response

__all__ = [
    "get_logger",
    "Component",
    "ComponentManager",
    "ComponentInitResult",
    "SystemStatus",
    "preprocess_llm_request",
    "handle_user_message",
    "update_l1_buffer",
    "create_components",
    "initialize_components",
    "shutdown_components",
    "handle_llm_response",
]
