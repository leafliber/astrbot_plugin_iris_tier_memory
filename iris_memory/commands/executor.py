"""
Iris Tier Memory - 指令执行器

处理 iris_mem 指令的解析和执行。
"""

from typing import TYPE_CHECKING

from iris_memory.core import get_logger
from .parser import CommandParser
from .registry import get_registry

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent

logger = get_logger("commands.executor")


async def execute_command(event: "AstrMessageEvent") -> None:
    """执行 iris_mem 指令
    
    解析指令并分发到对应的处理器执行。
    
    Args:
        event: AstrBot 消息事件对象
    """
    message_text = event.get_message_outline()
    parsed = CommandParser.parse(message_text)
    
    if not parsed.is_valid:
        await event.send_message(f"❌ {parsed.error_message}")
        return
    
    if parsed.module == "help" or parsed.module == "":
        await event.send_message(get_registry().get_help_text())
        return
    
    registry = get_registry()
    handler = registry.get_handler(parsed.module)
    
    if not handler:
        await event.send_message(f"❌ 未知的模块: {parsed.module}\n{registry.get_help_text()}")
        return
    
    if parsed.sub_command == "help":
        await event.send_message(handler.get_help_text())
        return
    
    target_user_id, error = await CommandParser.extract_target_user_id(event, parsed.args)
    if error:
        await event.send_message(f"❌ {error}")
        return
    
    if target_user_id:
        parsed.args.target_user_id = target_user_id
    
    try:
        result = await handler.handle(event, parsed.args, parsed.sub_command)
        await event.send_message(result.message)
    except Exception as e:
        logger.error(f"执行指令失败: {e}", exc_info=True)
        await event.send_message(f"❌ 执行指令失败: {e}")
