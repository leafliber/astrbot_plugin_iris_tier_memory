"""
插件生命周期管理模块

负责组件的创建、初始化和清理等生命周期管理。
"""
from typing import Optional, Tuple, TYPE_CHECKING
from datetime import datetime

from iris_memory.core import get_logger, ComponentManager, Component

if TYPE_CHECKING:
    from astrbot.api.star import Context

logger = get_logger("lifecycle")

# 全局组件管理器实例
_component_manager: Optional[ComponentManager] = None

# 全局启动时间
_start_time: Optional[datetime] = None


def set_component_manager(manager: ComponentManager) -> None:
    """设置全局组件管理器
    
    Args:
        manager: 组件管理器实例
    """
    global _component_manager, _start_time
    _component_manager = manager
    _start_time = datetime.now()
    logger.debug("已设置全局组件管理器")


def get_component_manager() -> ComponentManager:
    """获取全局组件管理器
    
    Returns:
        组件管理器实例
        
    Raises:
        RuntimeError: 如果组件管理器未初始化
    """
    if _component_manager is None:
        raise RuntimeError("组件管理器未初始化，请先调用 set_component_manager()")
    return _component_manager


def get_uptime() -> int:
    """获取运行时间（秒）
    
    Returns:
        运行时间（秒）
    """
    if _start_time is None:
        return 0
    
    delta = datetime.now() - _start_time
    return int(delta.total_seconds())


def create_components(context: "Context") -> Tuple[Component, ...]:
    """创建所有组件实例
    
    根据配置创建需要的组件实例，但暂不初始化。
    
    Args:
        context: AstrBot Context 对象
    
    Returns:
        组件元组
    """
    from iris_memory.config import get_config
    config = get_config()
    components = []
    
    # 阶段5: LLM 管理器（最先创建，其他组件可能依赖）
    from iris_memory.llm import LLMManager
    components.append(LLMManager(context))
    logger.debug("已添加 LLMManager 组件")
    
    # 阶段2: L1 消息缓冲
    if config.get("l1_buffer.enable"):
        from iris_memory.l1_buffer import L1Buffer
        components.append(L1Buffer())
        logger.debug("已添加 L1Buffer 组件")
    
    # 阶段3: L2 记忆库
    if config.get("l2_memory.enable"):
        # 延迟导入，避免循环依赖
        from iris_memory.l2_memory import L2MemoryAdapter
        
        # 获取当前人格 ID（如果启用人格隔离）
        persona_id = "default"
        if config.get("isolation_config.enable_persona_isolation"):
            # 尝试从 context 获取 persona_id
            # AstrBot 的 StarContext 可能有 persona_id 属性
            persona_id = getattr(context, 'persona_id', None)
            
            # 如果 context 没有 persona_id，尝试从内部 context 获取
            if not persona_id and hasattr(context, 'context'):
                inner_context = context.context
                persona_id = getattr(inner_context, 'persona_id', None)
            
            # 如果都没有，使用默认值
            persona_id = persona_id or 'default'
        
        components.append(L2MemoryAdapter(persona_id=persona_id))
        logger.debug(f"已添加 L2MemoryAdapter 组件，persona_id: {persona_id}")
    
    # 阶段4: L3 知识图谱
    if config.get("l3_kg.enable"):
        from iris_memory.l3_kg import L3KGAdapter
        components.append(L3KGAdapter())
        logger.debug("已添加 L3KGAdapter 组件")
    
    # 阶段6: 定时任务调度器
    from iris_memory.tasks import TaskScheduler
    components.append(TaskScheduler())
    logger.debug("已添加 TaskScheduler 组件")
    
    # 阶段9: 画像存储
    if config.get("profile.enable"):
        from iris_memory.profile import ProfileStorage
        components.append(ProfileStorage(context))
        logger.debug("已添加 ProfileStorage 组件")
    
    # 阶段10: 图片限额管理器
    if config.get("image_parsing.enable"):
        from iris_memory.image import ImageQuotaManager
        components.append(ImageQuotaManager(context))
        logger.debug("已添加 ImageQuotaManager 组件")
    
    return tuple(components)


async def initialize_components(
    component_manager: Optional[ComponentManager]
) -> bool:
    """初始化所有组件
    
    Args:
        component_manager: 组件管理器实例，如果为 None 则创建新的
    
    Returns:
        初始化是否成功
        
    Note:
        即使初始化失败也返回 True（已尝试初始化），避免重复尝试
    """
    if component_manager is None:
        logger.warning("组件管理器为 None，无法初始化组件")
        return False
    
    try:
        logger.info("开始异步初始化组件...")
        
        # 初始化所有组件
        results = await component_manager.initialize_all()
        
        # 统计初始化结果
        success_count = sum(1 for r in results if r.success)
        logger.info(f"组件初始化完成：{success_count}/{len(results)} 成功")
        
        # 注入 ComponentManager 引用到需要的组件
        _inject_component_manager(component_manager)
        
        # 启动定时任务
        await _start_scheduled_tasks(component_manager)
        
        return True
        
    except Exception as e:
        logger.error(f"组件初始化失败：{e}", exc_info=True)
        # 即使失败也返回 True，避免重复尝试
        return True


def _inject_component_manager(component_manager: ComponentManager) -> None:
    """注入 ComponentManager 引用到需要的组件
    
    某些组件需要延迟获取其他组件的引用（如 L1Buffer 需要 LLMManager），
    在组件初始化完成后注入 ComponentManager 引用。
    
    Args:
        component_manager: 组件管理器实例
    """
    # 注入到 L1Buffer
    l1_buffer = component_manager.get_component("l1_buffer")
    if l1_buffer and hasattr(l1_buffer, 'set_component_manager'):
        l1_buffer.set_component_manager(component_manager)
        logger.debug("已注入 ComponentManager 到 L1Buffer")
    
    # 注入到 TaskScheduler
    scheduler = component_manager.get_component("scheduler")
    if scheduler and hasattr(scheduler, 'set_component_manager'):
        scheduler.set_component_manager(component_manager)
        logger.debug("已注入 ComponentManager 到 TaskScheduler")


async def _start_scheduled_tasks(component_manager: ComponentManager) -> None:
    """启动定时任务
    
    注册并启动所有定时任务。
    
    Args:
        component_manager: 组件管理器实例
    """
    from iris_memory.config import get_config
    from iris_memory.tasks import TaskScheduler, ForgettingTask, MergeTask
    
    scheduler = component_manager.get_component("scheduler")
    if not scheduler or not scheduler.is_available:
        logger.warning("TaskScheduler 不可用，跳过启动定时任务")
        return
    
    config = get_config()
    
    # 注册遗忘清洗任务
    if config.get("scheduled_tasks.enable_forgetting"):
        forgetting_task = ForgettingTask(component_manager)
        interval_hours = config.get("forgetting_task_interval_hours")
        
        scheduler.register_periodic_task(
            task_name="forgetting",
            coro_func=forgetting_task.execute,
            interval_hours=interval_hours
        )
        logger.info(f"已注册遗忘清洗任务，间隔 {interval_hours} 小时")
    
    # 注册合并任务
    if config.get("scheduled_tasks.enable_merging"):
        merge_task = MergeTask(component_manager)
        interval_hours = config.get("merge_task_interval_hours")
        
        scheduler.register_periodic_task(
            task_name="merging",
            coro_func=merge_task.execute,
            interval_hours=interval_hours
        )
        logger.info(f"已注册记忆合并任务，间隔 {interval_hours} 小时")


async def shutdown_components(
    component_manager: Optional[ComponentManager]
) -> None:
    """关闭所有组件
    
    Args:
        component_manager: 组件管理器实例
    """
    if not component_manager:
        return
    
    try:
        await component_manager.shutdown_all()
        logger.info("组件关闭完成")
    except Exception as e:
        logger.error(f"组件关闭失败：{e}", exc_info=True)
