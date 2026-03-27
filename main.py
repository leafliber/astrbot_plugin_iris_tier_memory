"""
Iris Tier Memory - AstrBot 分层记忆插件

提供三阶段记忆管理：
- L1: 消息上下文缓冲
- L2: 记忆库（ChromaDB）
- L3: 知识图谱（KuzuDB）
"""

from pathlib import Path
from typing import Optional

from astrbot.api import AstrBotConfig
from astrbot.api.star import Context, Star, register

from iris_memory.config import init_config, get_config
from iris_memory.core import ComponentManager, get_logger


logger = get_logger("main")


@register("iris_tier_memory", "Iris Tier Memory", "Leaf", "1.0.0", "https://github.com/example/iris_tier_memory")
class IrisTierMemoryPlugin(Star):
    """AstrBot 分层记忆插件主类
    
    集成三阶段记忆系统，支持热重启和配置热修改。
    
    Attributes:
        config: 配置管理器
        component_manager: 组件生命周期管理器
        _initialized: 组件是否已异步初始化
    
    Examples:
        插件由 AstrBot 自动加载，构造函数接收配置：
        
        >>> plugin = IrisTierMemoryPlugin(context, config)
        >>> await plugin._ensure_initialized()  # 确保组件初始化
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        """初始化插件
        
        Args:
            context: AstrBot 插件上下文
            config: AstrBot 用户配置
        
        Notes:
            - 配置系统在此阶段初始化
            - 组件管理器在此阶段创建，但组件尚未初始化
            - 组件初始化通过 `_ensure_initialized()` 延迟执行
        """
        super().__init__(context)
        
        # 初始化配置系统
        data_dir = Path(context.get_data_dir())
        self.config = init_config(config, data_dir)
        logger.info(f"插件数据目录：{data_dir}")
        
        # 创建组件管理器（暂不初始化组件）
        # 组件将在第一次需要时通过 _ensure_initialized() 异步初始化
        self.component_manager: Optional[ComponentManager] = None
        self._initialized = False
        
        logger.info("Iris Tier Memory 插件已加载")
    
    async def _ensure_initialized(self) -> None:
        """确保组件已初始化
        
        延迟初始化模式：在第一次需要组件时执行异步初始化。
        如果初始化失败，仅 L1 层可用。
        
        Notes:
            - 使用标志位防止重复初始化
            - 初始化失败时记录错误但不抛出异常
        """
        if self._initialized:
            return
        
        try:
            logger.info("开始异步初始化组件...")
            
            # TODO: 在后续阶段创建各组件实例
            # 阶段2: L1 消息缓冲
            # 阶段3: ChromaDB 适配器
            # 阶段4: KuzuDB 适配器
            # 阶段5: LLM 管理器
            # 阶段6: 定时任务调度器
            # 阶段9: 画像存储
            # 阶段10: 图片限额管理器
            
            # 暂时创建空的组件管理器
            # 后续阶段会添加实际组件
            self.component_manager = ComponentManager(tuple())
            
            # 初始化所有组件
            results = await self.component_manager.initialize_all()
            
            # 统计初始化结果
            success_count = sum(1 for r in results if r.success)
            logger.info(f"组件初始化完成：{success_count}/{len(results)} 成功")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"组件初始化失败：{e}", exc_info=True)
            # 即使失败也标记为已初始化，避免重复尝试
            self._initialized = True
            # 使用空组件管理器，仅 L1 可用
            if self.component_manager is None:
                self.component_manager = ComponentManager(tuple())
    
    async def terminate(self):
        """插件卸载时的清理钩子
        
        当插件被卸载或停用时调用，负责清理所有组件资源。
        
        Notes:
            - 关闭所有已初始化的组件
            - 即使关闭失败也继续尝试关闭其他组件
            - 记录关闭过程中的所有错误
        """
        logger.info("开始关闭插件组件...")
        
        if self.component_manager:
            try:
                await self.component_manager.shutdown_all()
                logger.info("组件关闭完成")
            except Exception as e:
                logger.error(f"组件关闭失败：{e}", exc_info=True)
        
        logger.info("Iris Tier Memory 插件已卸载")
