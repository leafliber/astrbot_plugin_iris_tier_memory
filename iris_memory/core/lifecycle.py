"""
插件生命周期管理模块

负责组件的创建、初始化和清理等生命周期管理。
"""
from typing import Optional, Tuple

from iris_memory.config import get_config
from iris_memory.core import get_logger, ComponentManager, Component

logger = get_logger("lifecycle")


def create_components() -> Tuple[Component, ...]:
    """创建所有组件实例
    
    根据配置创建需要的组件实例，但暂不初始化。
    
    Returns:
        组件元组
    """
    config = get_config()
    components = []
    
    # 阶段2: L1 消息缓冲
    if config.get("l1_buffer.enable"):
        from iris_memory.l1_buffer import L1Buffer
        components.append(L1Buffer())
        logger.debug("已添加 L1Buffer 组件")
    
    # 阶段3: L2 记忆库
    if config.get("l2_memory.enable"):
        # 延迟导入，避免循环依赖
        from iris_memory.l2_memory import L2MemoryAdapter
        # TODO: 支持人格隔离时，从配置读取 persona_id
        components.append(L2MemoryAdapter(persona_id="default"))
        logger.debug("已添加 L2MemoryAdapter 组件")
    
    # 阶段4: L3 知识图谱
    if config.get("l3_kg.enable"):
        from iris_memory.l3_kg import L3KGAdapter
        components.append(L3KGAdapter())
        logger.debug("已添加 L3KGAdapter 组件")
    
    # TODO: 后续阶段添加更多组件
    # 阶段5: LLM 管理器
    # 阶段6: 定时任务调度器
    # 阶段9: 画像存储
    # 阶段10: 图片限额管理器
    
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
        
        return True
        
    except Exception as e:
        logger.error(f"组件初始化失败：{e}", exc_info=True)
        # 即使失败也返回 True，避免重复尝试
        return True


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
