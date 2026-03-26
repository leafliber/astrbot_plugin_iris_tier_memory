"""
Iris Tier Memory - AstrBot 分层记忆系统插件
"""

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("iris_tier_memory", "YourName", "分层记忆系统插件", "1.0.0")
class IrisTierMemoryPlugin(Star):
    """Iris Tier Memory 插件主类"""
    
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化方法"""
        logger.info("Iris Tier Memory 插件已初始化")

    @filter.command("iris")
    async def iris_command(self, event: AstrMessageEvent):
        """Iris 命令处理器"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        logger.info(f"收到来自 {user_name} 的消息: {message_str}")
        yield event.plain_result(f"Hello, {user_name}! Iris Memory 已就绪。")

    async def terminate(self):
        """插件销毁方法"""
        logger.info("Iris Tier Memory 插件已卸载")
