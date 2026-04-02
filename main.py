"""
Iris Tier Memory - AstrBot 分层记忆插件

提供三阶段记忆管理：
- L1: 消息上下文缓冲
- L2: 记忆库（ChromaDB）
- L3: 知识图谱（KuzuDB）
"""

import asyncio
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
    set_component_manager,
)
from iris_memory.tools import (
    SaveKnowledgeTool,
    SaveMemoryTool,
    ReadMemoryTool,
    CorrectMemoryTool,
    GetGroupProfileTool,
    GetUserProfileTool,
)
from iris_memory.web import WebServer, create_web_server_from_config
from iris_memory.commands import (
    get_registry,
    execute_command,
    L1CommandHandler,
    L2CommandHandler,
    L3CommandHandler,
    ProfileCommandHandler,
    AllCommandHandler,
)

logger = get_logger("main")


@register(
    "astrbot_plugin_iris_tier_memory",
    "Leafiber",
    "Iris Tier Memory",
    "1.0.0",
    "https://github.com/Leafliber/astrbot_plugin_iris_tier_memory"
)
class IrisTierMemoryPlugin(Star):
    """AstrBot 分层记忆插件主类
    
    集成三阶段记忆系统，支持热重启和配置热修改。
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context: Context = context
        
        # 初始化配置系统
        data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_iris_tier_memory"
        self.config: Config = init_config(config, data_dir)
        logger.info(f"插件数据目录：{data_dir}")
        
        # 创建组件管理器
        components = create_components(context, self)
        self.component_manager: Optional[ComponentManager] = ComponentManager(components)
        self._initialized: bool = False
        self._init_lock: asyncio.Lock = asyncio.Lock()
        
        # 设置全局组件管理器引用
        set_component_manager(self.component_manager)
        
        # 注册组件
        self._register_llm_tools()
        self._register_command_handlers()
        
        # 启动 Web 服务器
        self.web_server: Optional[WebServer] = None
        try:
            self.web_server = create_web_server_from_config()
            if self.web_server:
                self.web_server.start()
        except Exception as e:
            logger.error(f"初始化 Web 服务器失败：{e}", exc_info=True)
        
        logger.info("✅ Iris Tier Memory 插件已加载")
    
    def _register_llm_tools(self) -> None:
        """注册 LLM Tool"""
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
    
    def _register_command_handlers(self) -> None:
        """注册指令处理器"""
        try:
            registry = get_registry()
            handlers = [
                L1CommandHandler(),
                L2CommandHandler(),
                L3CommandHandler(),
                ProfileCommandHandler(),
                AllCommandHandler(),
            ]
            for handler in handlers:
                registry.register(handler)
            logger.info(f"已注册 {len(handlers)} 个指令处理器")
        except Exception as e:
            logger.error(f"注册指令处理器失败：{e}", exc_info=True)
    
    async def _ensure_initialized(self) -> None:
        """确保组件已初始化"""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await initialize_components(self.component_manager)
            self._initialized = True
    
    async def terminate(self):
        """插件卸载清理"""
        logger.info("开始关闭插件组件...")
        if self.web_server:
            self.web_server.shutdown()
        await shutdown_components(self.component_manager)
        logger.info("Iris Tier Memory 插件已卸载")
    
    # ========================================================================
    # AstrBot 钩子
    # ========================================================================
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent) -> None:
        """处理所有消息事件"""
        await self._ensure_initialized()
        if self.component_manager:
            await handle_user_message(event, self.component_manager)
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("iris_mem")
    async def iris_mem(self, event: AstrMessageEvent) -> None:
        """iris_mem 指令入口 - 管理员专用"""
        await self._ensure_initialized()
        if self.component_manager:
            await execute_command(event)
    
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req) -> None:
        """LLM 请求前钩子"""
        await self._ensure_initialized()
        if self.component_manager:
            await preprocess_llm_request(event, req, self.component_manager)
    
    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp) -> None:
        """LLM 响应后钩子"""
        await self._ensure_initialized()
        if self.component_manager:
            await handle_llm_response(event, resp, self.component_manager)
