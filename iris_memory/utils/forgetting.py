"""
Iris Tier Memory - 遗忘权重算法

实现记忆遗忘评分算法，用于评估记忆的重要性和淘汰优先级。

算法公式：S = w1·R + w2·F + w3·C + w4·(1 - D)

其中：
- R (Recency): 近因性 - 最近访问时间的影响
- F (Frequency): 频率性 - 访问次数的影响
- C (Confidence): 置信度 - 记忆质量的影响
- D (Degree): 孤立度 - 缺乏关联的影响（图谱中使用）

得分越高，记忆越重要，越不容易被淘汰。
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING

from iris_memory.config import get_config

if TYPE_CHECKING:
    from iris_memory.l2_memory.models import MemoryEntry


# ============================================================================
# 遗忘权重计算
# ============================================================================

def calculate_recency(
    last_access_time: Optional[str],
    lambda_decay: float = 0.1
) -> float:
    """计算近因性得分
    
    使用指数衰减函数计算近因性得分，最近访问的记忆得分更高。
    
    Args:
        last_access_time: 最近访问时间（ISO 格式字符串）
        lambda_decay: 衰减系数，越大则衰减越快
    
    Returns:
        近因性得分 [0, 1]，越接近 1 表示越近期访问
    
    Examples:
        >>> now = datetime.now().isoformat()
        >>> calculate_recency(now)
        1.0
        >>> old_time = (datetime.now() - timedelta(days=30)).isoformat()
        >>> calculate_recency(old_time)
        0.05
    """
    if not last_access_time:
        # 无访问记录，使用创建时间的一半得分
        return 0.5
    
    try:
        access_dt = datetime.fromisoformat(last_access_time)
        now = datetime.now()
        days_elapsed = (now - access_dt).total_seconds() / 86400
        
        # 指数衰减：exp(-lambda * t)
        recency = 2.71828 ** (-lambda_decay * days_elapsed)
        return max(0.0, min(1.0, recency))
    
    except (ValueError, TypeError):
        return 0.5


def calculate_frequency(access_count: int, max_count: int = 100) -> float:
    """计算频率性得分
    
    使用对数函数计算频率得分，访问次数越多得分越高。
    
    Args:
        access_count: 访问次数
        max_count: 参考最大访问次数（用于归一化）
    
    Returns:
        频率性得分 [0, 1]，越接近 1 表示访问越频繁
    
    Examples:
        >>> calculate_frequency(0)
        0.0
        >>> calculate_frequency(10)
        0.52
        >>> calculate_frequency(100)
        1.0
    """
    if access_count <= 0:
        return 0.0
    
    # 对数归一化：log(count + 1) / log(max_count + 1)
    import math
    normalized = math.log(access_count + 1) / math.log(max_count + 1)
    return max(0.0, min(1.0, normalized))


def calculate_confidence(confidence: float) -> float:
    """计算置信度得分
    
    直接返回置信度值，假设置信度已在 [0, 1] 范围内。
    
    Args:
        confidence: 原始置信度值
    
    Returns:
        置信度得分 [0, 1]
    
    Examples:
        >>> calculate_confidence(0.85)
        0.85
    """
    return max(0.0, min(1.0, confidence))


def calculate_isolation_degree(metadata: Dict[str, Any]) -> float:
    """计算孤立度得分
    
    孤立度表示记忆缺乏关联的程度。在 L2 阶段暂时返回固定值，
    在 L3 知识图谱阶段会根据节点连接数计算。
    
    Args:
        metadata: 记忆元数据（预留参数）
    
    Returns:
        孤立度得分 [0, 1]，越接近 1 表示越孤立
    
    Note:
        L2 阶段默认返回 0.5（中等孤立度），
        L3 阶段会根据图谱连接数动态计算。
    """
    # TODO: L3 阶段根据图谱连接数计算
    # connected_count = metadata.get("connected_count", 0)
    # isolation = 1.0 / (connected_count + 1)
    return 0.5


def calculate_forgetting_score(
    entry: "MemoryEntry",
    weights: Dict[str, float] = None
) -> float:
    """计算综合遗忘评分
    
    综合考虑近因性、频率性、置信度和孤立度，计算记忆的重要性得分。
    得分越高，记忆越重要，越不容易被淘汰。
    
    公式：S = w1·R + w2·F + w3·C + w4·(1 - D)
    
    Args:
        entry: 记忆条目
        weights: 权重字典，包含 w1, w2, w3, w4
    
    Returns:
        综合评分 [0, 1]，越接近 1 表示越重要
    
    Examples:
        >>> from iris_memory.l2_memory.models import MemoryEntry
        >>> entry = MemoryEntry(
        ...     id="mem_001",
        ...     content="测试记忆",
        ...     metadata={
        ...         "last_access_time": datetime.now().isoformat(),
        ...         "access_count": 5,
        ...         "confidence": 0.85
        ...     }
        ... )
        >>> score = calculate_forgetting_score(entry)
        >>> 0 < score < 1
        True
    """
    config = get_config()
    
    # 获取权重配置
    if weights is None:
        weights = {
            "w1": 0.3,  # 近因性权重
            "w2": 0.3,  # 频率性权重
            "w3": 0.2,  # 置信度权重
            "w4": 0.2,  # 孤立度权重
        }
    
    # 获取隐藏配置
    lambda_decay = config.get("forgetting_lambda")
    
    # 计算各维度得分
    R = calculate_recency(
        entry.last_access_time,
        lambda_decay=lambda_decay
    )
    F = calculate_frequency(entry.access_count)
    C = calculate_confidence(entry.confidence)
    D = calculate_isolation_degree(entry.metadata)
    
    # 加权求和：S = w1·R + w2·F + w3·C + w4·(1 - D)
    score = (
        weights["w1"] * R +
        weights["w2"] * F +
        weights["w3"] * C +
        weights["w4"] * (1 - D)
    )
    
    return max(0.0, min(1.0, score))


def should_evict(
    entry: "MemoryEntry",
    threshold: float = 0.3,
    retention_days: int = 30
) -> bool:
    """判断记忆是否应该被淘汰
    
    综合考虑遗忘评分和保留期，判断记忆是否应该被淘汰。
    
    淘汰条件：
    1. 遗忘评分低于阈值（默认 0.3）
    2. 距上次访问超过保留期（默认 30 天）
    
    Args:
        entry: 记忆条目
        threshold: 遗忘阈值
        retention_days: 保留期天数
    
    Returns:
        是否应该被淘汰
    
    Examples:
        >>> from iris_memory.l2_memory.models import MemoryEntry
        >>> entry = MemoryEntry(
        ...     id="mem_001",
        ...     content="旧记忆",
        ...     metadata={
        ...         "last_access_time": "2024-01-01T00:00:00",
        ...         "access_count": 0,
        ...         "confidence": 0.1
        ...     }
        ... )
        >>> should_evict(entry)
        True
    """
    config = get_config()
    threshold = config.get("forgetting_threshold")
    
    # 计算遗忘评分
    score = calculate_forgetting_score(entry)
    
    if score < threshold:
        # 评分低于阈值，检查保留期
        last_access = entry.last_access_time
        if last_access:
            try:
                access_dt = datetime.fromisoformat(last_access)
                days_elapsed = (datetime.now() - access_dt).days
                
                if days_elapsed > retention_days:
                    return True
            except (ValueError, TypeError):
                pass
        else:
            # 无访问记录，根据评分决定
            return True
    
    return False
