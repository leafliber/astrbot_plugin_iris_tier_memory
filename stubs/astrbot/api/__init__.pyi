"""Type stubs for astrbot.api"""

from typing import Any, Dict

class AstrBotConfig(Dict[str, Any]):
    """AstrBot 配置类
    
    继承自 dict，支持字典操作和配置管理
    """
    config_path: str
    default_config: dict
    schema: dict | None
    
    def __init__(
        self,
        config_path: str = ...,
        default_config: dict = ...,
        schema: dict | None = None,
    ) -> None: ...
    
    def save_config(self) -> None: ...
    def check_exist(self) -> bool: ...

# 其他导出
class FunctionTool:
    """LLM 工具函数"""
    ...

class ToolSet:
    """工具集合"""
    ...

class BaseFunctionToolExecutor:
    """工具执行器基类"""
    ...

def register_agent(...) -> Any: ...
def register_llm_tool(...) -> Any: ...

__all__ = [
    "AstrBotConfig",
    "BaseFunctionToolExecutor",
    "FunctionTool",
    "ToolSet",
    "agent",
    "llm_tool",
    "logger",
]
