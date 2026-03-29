"""
Iris Tier Memory - 定时任务模块

提供定时任务调度和执行功能，包括：
- TaskScheduler: 任务调度器（管理后台任务生命周期）
- ForgettingTask: 遗忘清洗任务
- MergeTask: 记忆合并任务
"""

from iris_memory.core import get_logger

# 延迟导入，避免循环依赖
__all__ = ["TaskScheduler", "ForgettingTask", "MergeTask"]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


logger = get_logger("tasks")
logger.debug("定时任务模块已加载")
