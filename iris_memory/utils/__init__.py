"""
Iris Tier Memory - 公共工具模块

提供通用工具函数，供各模块使用。
"""

from .token_counter import count_tokens, get_encoder
from .forgetting import (
    calculate_recency,
    calculate_frequency,
    calculate_confidence,
    calculate_isolation_degree,
    calculate_forgetting_score,
    should_evict,
)

__all__ = [
    # Token 计数
    "count_tokens",
    "get_encoder",
    
    # 遗忘权重算法
    "calculate_recency",
    "calculate_frequency",
    "calculate_confidence",
    "calculate_isolation_degree",
    "calculate_forgetting_score",
    "should_evict",
]
