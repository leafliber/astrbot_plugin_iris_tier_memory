"""
Iris Tier Memory - LLM 调用接口

定义 LLM 调用协议接口，供各模块使用。
阶段 5 已实现 LLMManager，总结功能正式可用。
"""

from typing import Protocol, runtime_checkable


# ============================================================================
# 协议接口定义
# ============================================================================

@runtime_checkable
class LLMCaller(Protocol):
    """LLM 调用协议接口
    
    定义统一的 LLM 调用接口，供 Summarizer 等模块使用。
    
    阶段 5：LLMManager 实现此接口，总结功能正式可用
    
    Methods:
        call: 调用 LLM 生成响应
    
    Examples:
        >>> class SimpleLLMCaller:
        ...     async def call(self, prompt: str, provider: str = "") -> str:
        ...         return "Response"
        ...
        >>> caller = SimpleLLMCaller()
        >>> isinstance(caller, LLMCaller)
        True
    """
    
    async def call(self, prompt: str, provider: str = "") -> str:
        """调用 LLM 生成响应
        
        Args:
            prompt: 输入提示词
            provider: 模型提供商（可选，留空使用默认）
        
        Returns:
            LLM 生成的响应文本
        
        Raises:
            Exception: LLM 调用失败时抛出
        """
        ...
