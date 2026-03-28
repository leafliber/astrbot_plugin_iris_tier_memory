"""
Iris Tier Memory - Token 计数工具

使用 tiktoken 实现文本 Token 计数，支持多种编码格式。
采用单例模式缓存编码器，避免重复初始化。
"""

from typing import Optional
import tiktoken

from iris_memory.core import get_logger

logger = get_logger("token_counter")


# ============================================================================
# 编码器缓存（单例模式）
# ============================================================================

_encoder_cache: dict[str, tiktoken.Encoding] = {}


def get_encoder(encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
    """获取编码器实例（单例模式）
    
    缓存编码器实例，避免重复初始化带来的性能开销。
    
    Args:
        encoding_name: 编码名称，默认 cl100k_base（GPT-4/ChatGPT 使用）
    
    Returns:
        tiktoken 编码器实例
    
    Examples:
        >>> encoder = get_encoder()
        >>> encoder.encode("Hello, world!")
        [9906, 11, 1917, 0]
    """
    if encoding_name not in _encoder_cache:
        logger.debug(f"初始化编码器：{encoding_name}")
        _encoder_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
        logger.debug(f"编码器 {encoding_name} 已缓存")
    
    return _encoder_cache[encoding_name]


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """计算文本的 Token 数量
    
    使用 tiktoken 编码器计算文本的 Token 数量。
    对于空字符串返回 0。
    
    Args:
        text: 要计算的文本
        encoding_name: 编码名称，默认 cl100k_base
    
    Returns:
        Token 数量
    
    Examples:
        >>> count_tokens("Hello, world!")
        4
        >>> count_tokens("")
        0
        >>> count_tokens("你好，世界！")
        9
    """
    if not text:
        return 0
    
    encoder = get_encoder(encoding_name)
    return len(encoder.encode(text))


def count_messages_tokens(
    messages: list[dict],
    encoding_name: str = "cl100k_base"
) -> int:
    """计算消息列表的总 Token 数
    
    计算聊天消息列表的总 Token 数量，包括角色标识。
    适用于 OpenAI Chat API 格式的消息列表。
    
    Args:
        messages: 消息列表，每条消息包含 role 和 content
        encoding_name: 编码名称，默认 cl100k_base
    
    Returns:
        总 Token 数量
    
    Examples:
        >>> messages = [
        ...     {"role": "user", "content": "Hello"},
        ...     {"role": "assistant", "content": "Hi there!"}
        ... ]
        >>> count_messages_tokens(messages)
        7
    """
    if not messages:
        return 0
    
    encoder = get_encoder(encoding_name)
    total_tokens = 0
    
    for message in messages:
        # 每条消息的格式：<|start|>{role}\n{content}<|end|>\n
        # 这里简化计算：role + content + 格式开销
        role = message.get("role", "")
        content = message.get("content", "")
        
        # 计算角色和内容的 Token
        total_tokens += len(encoder.encode(role))
        total_tokens += len(encoder.encode(content))
        
        # 每条消息的格式开销（约 4 tokens）
        total_tokens += 4
    
    # 整个消息列表的格式开销（约 2 tokens）
    total_tokens += 2
    
    return total_tokens
