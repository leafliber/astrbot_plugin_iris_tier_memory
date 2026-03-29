"""
Iris Tier Memory - AstrBot 分层记忆插件

提供三阶段记忆管理：
- L1: 消息上下文缓冲
- L2: 记忆库（ChromaDB）
- L3: 知识图谱（KuzuDB）
"""

import sys
from pathlib import Path
from typing import Optional

# 模块导入支持
plugin_root = Path(__file__).parent
if str(plugin_root) not in sys.path:
    sys.path.insert(0, str(plugin_root))
from iris_memory.config import init_config, Config

from astrbot.api import AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from iris_memory.core import (
    ComponentManager,
    get_logger,
    create_components,
    initialize_components,
    shutdown_components,
    handle_user_message,
    preprocess_llm_request,
    handle_llm_response,
)
from iris_memory.tools import (
    SaveKnowledgeTool,
    SaveMemoryTool,
    ReadMemoryTool,
    CorrectMemoryTool,
    GetGroupProfileTool,
    GetUserProfileTool,
)
# from iris_memory.web import register_routes  # TODO: Web 模块暂时禁用

logger = get_logger("main")


@register(
    "iris_tier_memory",
    "Iris Tier Memory",
    "Leaf",
    "1.0.0",
    "https://github.com/example/iris_tier_memory"
)
class IrisTierMemoryPlugin(Star):
    """AstrBot 分层记忆插件主类
    
    集成三阶段记忆系统，支持热重启和配置热修改。
    
    Attributes:
        config: 配置管理器
        component_manager: 组件生命周期管理器
        _initialized: 组件是否已异步初始化
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        """初始化插件
        
        Args:
            context: AstrBot 插件上下文
            config: AstrBot 用户配置
        """
        super().__init__(context)
        self.context: Context = context
        
        # 初始化配置系统
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "nonebot_plugin_iris_tier_memory"
        self.config: Config = init_config(config, data_dir)
        logger.info(f"插件数据目录：{data_dir}")
        
        # 创建组件管理器（暂不初始化组件）
        components = create_components(context)
        self.component_manager: Optional[ComponentManager] = ComponentManager(components)
        self._initialized: bool = False
        
        # 注册 LLM Tool
        self._register_llm_tools()
        
        # TODO: Web 模块暂时禁用
        # AstrBot Context 类没有 app 属性，无法直接注册 Quart Blueprint
        # 可能的解决方案：
        # 1. 使用 AstrBot 提供的 HTTP API 机制（待研究）
        # 2. 将 Web 模块作为独立服务运行
        # 3. 通过其他方式（如事件处理器）提供 Web 功能
        
        # try:
        #     register_routes(context.app)
        #     logger.info("✅ Web 模块已加载")
        # except Exception as e:
        #     logger.error(f"❌ 加载 Web 模块失败：{e}", exc_info=True)
        
        logger.info("Iris Tier Memory 插件已加载")
    
    def _register_llm_tools(self) -> None:
        """注册所有 LLM Tool 到 AstrBot"""
        try:
            tools = [
                SaveKnowledgeTool(),
                SaveMemoryTool(),
                ReadMemoryTool(),
                CorrectMemoryTool(),
                GetGroupProfileTool(),
                GetUserProfileTool(),
            ]
            
            for tool in tools:
                self.context.add_llm_tools(tool)
            
            logger.info(f"已注册 {len(tools)} 个 LLM Tool")
        
        except Exception as e:
            logger.error(f"注册 LLM Tool 失败：{e}", exc_info=True)
    
    async def _ensure_initialized(self) -> None:
        """确保组件已初始化（延迟初始化模式）"""
        if self._initialized:
            return
        
        await initialize_components(self.component_manager)
        self._initialized = True
    
    async def terminate(self):
        """插件卸载时的清理钩子"""
        logger.info("开始关闭插件组件...")
        await shutdown_components(self.component_manager)
        logger.info("Iris Tier Memory 插件已卸载")
    
    # ========================================================================
    # AstrBot 钩子
    # ========================================================================
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent) -> None:
        """处理所有消息事件
        
        Args:
            event: AstrBot 消息事件对象
        """
        await self._ensure_initialized()
        if not self.component_manager:
            return
        
        await handle_user_message(event, self.component_manager)
    
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req) -> None:
        """LLM 请求前的钩子
        
        Args:
            event: AstrBot 消息事件对象
            req: LLM 提供者请求对象
        """
        await self._ensure_initialized()
        if not self.component_manager:
            return
        
        await preprocess_llm_request(event, req, self.component_manager)
    
    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp) -> None:
        """LLM 响应后的钩子
        
        Args:
            event: AstrBot 消息事件对象
            resp: LLM 响应对象
        """
        await self._ensure_initialized()
        if not self.component_manager:
            return
        
        await handle_llm_response(event, resp, self.component_manager)
