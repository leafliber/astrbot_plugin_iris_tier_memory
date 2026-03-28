"""
Iris Tier Memory - L2 记忆库降级逻辑

实现 L2 记忆库的降级和兜底机制。
"""

from typing import List

from iris_memory.core import get_logger
from .models import MemoryEntry, MemorySearchResult

logger = get_logger("l2_memory.fallback")


class FallbackRetriever:
    """降级检索器
    
    当 L2 记忆库不可用时使用的降级检索器。
    返回空结果，确保主流程不中断。
    
    Examples:
        >>> fallback = FallbackRetriever()
        >>> results = await fallback.retrieve("测试查询")
        >>> len(results)
        0
    """
    
    async def retrieve(
        self,
        query: str,
        group_id: str = None,
        top_k: int = 10
    ) -> List[MemorySearchResult]:
        """降级检索
        
        返回空结果列表。
        
        Args:
            query: 查询文本
            group_id: 群聊 ID（忽略）
            top_k: 返回数量（忽略）
        
        Returns:
            空列表
        """
        logger.debug(f"L2 记忆库降级模式，跳过检索：{query[:50]}...")
        return []
    
    async def add_memory(
        self,
        content: str,
        metadata: dict = None
    ) -> None:
        """降级写入
        
        记录警告日志，不执行写入。
        
        Args:
            content: 记忆内容
            metadata: 元数据
        """
        logger.warning(f"L2 记忆库降级模式，跳过写入：{content[:50]}...")


def check_chromadb_available() -> bool:
    """检查 ChromaDB 是否可用
    
    尝试导入 ChromaDB，判断是否可用。
    
    Returns:
        ChromaDB 是否可用
    """
    try:
        import chromadb
        return True
    except ImportError:
        logger.warning("ChromaDB 未安装，L2 记忆库将降级运行")
        return False


def create_fallback_handler():
    """创建降级处理器
    
    Returns:
        FallbackRetriever 实例
    """
    return FallbackRetriever()
