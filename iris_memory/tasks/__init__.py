"""
Iris Tier Memory - 定时任务模块

提供定时任务调度和执行功能，包括：
- TaskScheduler: 任务调度器（管理后台任务生命周期）
- ForgettingTask: 遗忘清洗任务
- MergeTask: 记忆合并任务
- ImageCacheCleanupTask: 图片缓存清理任务
- KGExtractionTask: L3 知识图谱提取任务
"""

from iris_memory.core import get_logger

__all__ = ["TaskScheduler", "ForgettingTask", "MergeTask", "ImageCacheCleanupTask", "KGExtractionTask"]


def __getattr__(name: str):
    """延迟导入模块成员"""
    if name == "TaskScheduler":
        from .scheduler import TaskScheduler
        return TaskScheduler
    elif name == "ForgettingTask":
        from .forgetting_task import ForgettingTask
        return ForgettingTask
    elif name == "MergeTask":
        from .merge_task import MergeTask
        return MergeTask
    elif name == "ImageCacheCleanupTask":
        from .cache_cleanup_task import ImageCacheCleanupTask
        return ImageCacheCleanupTask
    elif name == "KGExtractionTask":
        from .kg_extraction_task import KGExtractionTask
        return KGExtractionTask
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


logger = get_logger("tasks")
logger.debug("定时任务模块已加载")
