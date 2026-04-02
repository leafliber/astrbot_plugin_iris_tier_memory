"""
消息钩子处理模块

负责处理用户发送的消息钩子，包括：
- 添加用户消息到 L1 Buffer
- 用户画像更新
- 图片解析（all 模式）
"""
from typing import TYPE_CHECKING, cast

from iris_memory.core import get_logger

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
    3. 图片入队到 L1 Buffer 图片队列
    4. 图片解析（all 模式）
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    await _add_to_l1_buffer(event, component_manager)
    await _update_user_profile(event, component_manager)
    await _queue_images_to_l1_buffer(event, component_manager)
    await _parse_images_if_enabled(event, component_manager)


async def _add_to_l1_buffer(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """添加用户消息到 L1 Buffer（内部函数）
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    from iris_memory.platform import get_adapter
    
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
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    
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
    from iris_memory.platform import get_adapter
    
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


async def _queue_images_to_l1_buffer(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """提取图片并入队到 L1 Buffer 图片队列（内部函数）
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    from iris_memory.image import ImageQueueItem, ImageParseStatus
    import hashlib
    
    config = get_config()
    if not config.get("image_parsing.enable"):
        return
    
    adapter = get_adapter(event)
    images = adapter.get_images(event)
    
    if not images:
        return
    
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        return
    
    l1_buffer = cast("L1Buffer", buffer)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    raw_msg = adapter.get_raw_message(event)
    message_id = raw_msg.get("message_id", "")
    
    for image_info in images:
        image_hash = ""
        if image_info.url:
            image_hash = hashlib.md5(image_info.url.encode()).hexdigest()
        elif image_info.file_path:
            image_hash = hashlib.md5(image_info.file_path.encode()).hexdigest()
        
        if not image_hash:
            continue
        
        queue_item = ImageQueueItem(
            image_hash=image_hash,
            image_url=image_info.url or "",
            image_info=image_info,
            message_id=message_id,
            group_id=group_id,
            user_id=user_id,
            status=ImageParseStatus.PENDING
        )
        
        l1_buffer.add_image(group_id, queue_item)
    
    logger.debug(f"已入队 {len(images)} 张图片到 L1 Buffer 图片队列")


async def _parse_images_if_enabled(
    event: "AstrMessageEvent",
    component_manager: "ComponentManager"
) -> None:
    """解析图片（all 模式）
    
    仅在 all 模式下解析图片。
    related 模式在 LLM 请求钩子中处理。
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    from iris_memory.image import ImageParser, ImageParseStatus, ImageParseCache
    
    config = get_config()
    if not config.get("image_parsing.enable"):
        return
    
    mode = config.get("image_parsing.parsing_mode", "related")
    
    if mode == "related":
        return
    
    if mode != "all":
        logger.warning(f"未知的图片解析模式：{mode}")
        return
    
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        return
    
    l1_buffer = cast("L1Buffer", buffer)
    
    cache_manager = component_manager.get_component("image_cache")
    quota_manager = component_manager.get_component("image_quota")
    llm_manager = component_manager.get_component("llm_manager")
    
    if not llm_manager or not llm_manager.is_available:
        logger.warning("LLM Manager 不可用，跳过图片解析")
        return
    
    max_parse = config.get("image_parsing.max_parse_per_request", 5)
    pending_images = l1_buffer.get_images(group_id, limit=max_parse, only_pending=True)
    
    if not pending_images:
        return
    
    images_to_parse = []
    for img_item in pending_images:
        if cache_manager and cache_manager.is_available:
            cached = await cache_manager.get_cache(img_item.image_hash)
            if cached:
                l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.SUCCESS)
                continue
        
        images_to_parse.append(img_item)
    
    if not images_to_parse:
        return
    
    if quota_manager and quota_manager.is_available:
        has_quota = await quota_manager.check_quota()
        if not has_quota:
            logger.info("图片解析配额已耗尽，跳过解析")
            return
        
        quota_used = await quota_manager.use_quota(len(images_to_parse))
        if not quota_used:
            logger.warning("图片解析配额使用失败")
            return
    
    provider = config.get("image_parsing.provider", "")
    parser = ImageParser(llm_manager, provider)
    
    logger.info(f"开始解析 {len(images_to_parse)} 张图片（all 模式）")
    
    from iris_memory.image import ImageInfo
    image_infos = [
        img.image_info for img in images_to_parse 
        if img.image_info and img.image_info.has_url
    ]
    
    if not image_infos:
        return
    
    parse_results = await parser.parse_batch(image_infos)
    
    success_count = 0
    for i, result in enumerate(parse_results):
        if i >= len(images_to_parse):
            break
        
        img_item = images_to_parse[i]
        
        if not result.success:
            logger.warning(f"图片解析失败：{result.error_message}")
            l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.FAILED)
            continue
        
        if not result.content:
            logger.debug("图片解析结果为空")
            l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.FAILED)
            continue
        
        if cache_manager and cache_manager.is_available:
            cache = ImageParseCache(
                image_hash=img_item.image_hash,
                content=result.content,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens
            )
            await cache_manager.set_cache(cache)
        
        l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.SUCCESS)
        
        await l1_buffer.add_message(
            group_id=group_id,
            role="user",
            content=f"[图片内容] {result.content}",
            source=img_item.user_id
        )
        
        success_count += 1
    
    logger.info(f"已解析 {success_count}/{len(images_to_parse)} 张图片")
