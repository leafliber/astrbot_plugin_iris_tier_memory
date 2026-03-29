"""
消息钩子处理模块

负责处理用户发送的消息钩子，包括：
- 添加用户消息到 L1 Buffer
- 用户画像更新
- 关键词检测（未来扩展）
"""
from typing import TYPE_CHECKING, cast

from iris_memory.core import get_logger
from iris_memory.platform import get_adapter
from iris_memory.config import get_config

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent
    from iris_memory.core.components import ComponentManager
    from iris_memory.l1_buffer import L1Buffer

logger = get_logger("message_hook")


async def handle_user_message(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """处理用户消息钩子
    
    执行所有用户消息的处理逻辑（按顺序执行）：
    1. 添加用户消息到 L1 Buffer
    2. 用户画像更新
    3. TODO: 关键词检测（阶段 7）
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    await _add_to_l1_buffer(event, component_manager)
    await _update_user_profile(event, component_manager)
    # TODO: 关键词检测
    # await _detect_keywords(event, component_manager)


async def _add_to_l1_buffer(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """添加用户消息到 L1 Buffer（内部函数）
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    # 先检查消息内容，避免不必要的 adapter 调用
    content = event.message_str
    if not content:
        logger.debug("消息内容为空，跳过添加")
        return
    
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.debug("L1 Buffer 组件不可用，跳过消息添加")
        return
    
    # 类型转换：get_component 返回 Component，实际为 L1Buffer
    l1_buffer = cast("L1Buffer", buffer)
    
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    await l1_buffer.add_message(
        group_id=group_id,
        role="user",
        content=content,
        source=user_id
    )
    
    logger.debug(f"已添加用户消息到群聊 {group_id} 的 L1 Buffer")


async def _update_user_profile(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """更新用户画像（内部函数）
    
    在用户发送消息时更新画像简单字段。
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    # 1. 检查是否启用画像系统
    config = get_config()
    if not config.get("profile.enable"):
        return
    
    # 2. 获取 ProfileStorage 组件
    profile_storage = component_manager.get_component("profile")
    if not profile_storage or not profile_storage.is_available:
        logger.debug("画像系统组件不可用，跳过画像更新")
        return
    
    # 3. 获取群聊ID和用户ID
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    user_name = adapter.get_user_name(event)
    
    if not user_id:
        logger.debug("无法获取用户ID，跳过画像更新")
        return
    
    # 4. 根据群聊隔离配置决定 group_id
    effective_group_id = group_id if config.get("isolation_config.enable_group_isolation") else "default"
    
    # 5. 更新用户画像简单字段
    from iris_memory.profile import UserProfileManager
    
    user_manager = UserProfileManager(profile_storage)
    await user_manager.update_simple_fields(
        user_id=user_id,
        group_id=effective_group_id,
        user_name=user_name
    )
    
    logger.debug(f"已更新用户画像: {user_id} (群聊: {effective_group_id})")


async def update_l1_buffer(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager",
    role: str,
    content: str
) -> None:
    """更新 L1 Buffer（添加用户消息或助手响应）
    
    此函数用于特殊场景（如添加助手响应），
    普通用户消息应使用 handle_user_message() 处理。
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
        role: 消息角色（"user" 或 "assistant"）
        content: 消息内容
    """
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.debug("L1 Buffer 组件不可用，跳过消息更新")
        return
    
    # 类型转换：get_component 返回 Component，实际为 L1Buffer
    l1_buffer = cast("L1Buffer", buffer)
    
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    await l1_buffer.add_message(
        group_id=group_id,
        role=role,
        content=content,
        source=user_id if role == "user" else "assistant"
    )
    
    logger.debug(f"已添加 {role} 消息到群聊 {group_id} 的 L1 Buffer")
