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
    await _queue_images_to_l1_buffer(event, component_manager)
    await _parse_images_if_enabled(event, component_manager)


async def _update_profile_names(
    component_manager: "ComponentManager",
    group_id: str,
    group_name: str,
    user_id: str,
    user_name: str
) -> None:
    """更新用户昵称和群聊名称（内部函数）
    
    当用户昵称或群聊名称发生变化时，更新画像中的名称字段。
    用户昵称变化会记录到 historical_names。
    
    Args:
        component_manager: 组件管理器实例
        group_id: 群聊ID
        group_name: 群聊名称
        user_id: 用户ID
        user_name: 用户昵称
    """
    from iris_memory.config import get_config
    
    config = get_config()
    if not config.get("profile.enable"):
        return
    
    profile_storage = component_manager.get_component("profile")
    if not profile_storage or not profile_storage.is_available:
        return
    
    try:
        from iris_memory.profile import GroupProfileManager, UserProfileManager
        
        group_manager = GroupProfileManager(profile_storage)
        user_manager = UserProfileManager(profile_storage)
        
        effective_group_id = group_id if config.get("isolation_config.enable_group_isolation") else "default"
        
        if group_name:
            await group_manager.update_group_name(group_id, group_name)
        
        if user_name:
            await user_manager.update_user_name(user_id, effective_group_id, user_name)
        
    except Exception as e:
        logger.error(f"更新画像名称失败: {e}", exc_info=True)


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
    
    content = event.message_str
    if not content:
        logger.debug("消息内容为空，跳过添加")
        return
    
    from iris_memory.utils import sanitize_input
    content = sanitize_input(content, source="user_message")
    
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.debug("L1 Buffer 组件不可用，跳过消息添加")
        return
    
    l1_buffer = cast("L1Buffer", buffer)
    
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    user_name = adapter.get_user_name(event)
    group_name = adapter.get_group_name(event)
    
    metadata = {}
    if user_name:
        metadata["user_name"] = user_name
    
    await l1_buffer.add_message(
        group_id=group_id,
        role="user",
        content=content,
        source=user_id,
        metadata=metadata
    )
    
    logger.debug(f"已添加用户消息到群聊 {group_id} 的 L1 Buffer")
    
    await _update_profile_names(
        component_manager, group_id, group_name, user_id, user_name
    )


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
    
    支持 pHash 感知哈希去重和无效图过滤。
    
    Args:
        event: AstrBot 消息事件对象
        component_manager: 组件管理器实例
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    from iris_memory.image import ImageQueueItem, ImageParseStatus
    from iris_memory.image.image_utils import compute_image_hash, is_similar_image, check_invalid_image
    
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
    
    use_phash = config.get("image_phash_enable")
    phash_threshold = config.get("image_phash_threshold")
    use_filter = config.get("image_filter_enable")
    
    existing_hashes: list[str] = []
    if use_phash:
        for queue_key, img_list in l1_buffer._image_queues.items():
            for img in img_list:
                if img.image_hash.startswith("ph:"):
                    existing_hashes.append(img.image_hash)
    
    queued_count = 0
    for image_info in images:
        image_hash = await compute_image_hash(
            url=image_info.url,
            use_phash=use_phash
        )
        
        if not image_hash:
            continue
        
        if use_phash and image_hash.startswith("ph:"):
            is_dup = False
            for existing in existing_hashes:
                if is_similar_image(image_hash, existing, threshold=phash_threshold):
                    is_dup = True
                    logger.debug(f"pHash 去重：跳过相似图片 {image_hash[:16]}...")
                    break
            if is_dup:
                continue
            existing_hashes.append(image_hash)
        
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
        queued_count += 1
    
    if queued_count > 0:
        logger.debug(f"已入队 {queued_count} 张图片到 L1 Buffer 图片队列")


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
