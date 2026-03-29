"""
LLM 请求钩子处理模块

负责处理 LLM 请求前的钩子逻辑，包括：
- L1 上下文注入
- 用户画像注入
- 图片解析（related 模式）
- 知识图谱检索结果注入（未来扩展）
"""
from typing import TYPE_CHECKING, cast

from iris_memory.core import get_logger
from iris_memory.platform import get_adapter

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent
    from astrbot.api.provider import ProviderRequest
    from iris_memory.core.components import ComponentManager
    from iris_memory.l1_buffer import L1Buffer
    from iris_memory.profile import GroupProfileManager, UserProfileManager
    from iris_memory.profile.models import GroupProfile, UserProfile

logger = get_logger("llm_request_hook")


async def preprocess_llm_request(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> None:
    """LLM 请求钩子处理
    
    执行所有 LLM 对话前的预处理逻辑（按顺序执行）：
    1. L1 上下文注入
    2. 用户画像注入
    3. 图片解析（related 模式）
    4. TODO: 知识图谱检索结果注入（阶段 4）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    await _inject_l1_context(event, req, component_manager)
    await _inject_user_profile(event, req, component_manager)
    await _parse_images_if_related_mode(event, req, component_manager)
    # TODO: 知识图谱检索结果注入
    # await _inject_knowledge_graph(event, req, component_manager)


async def _inject_l1_context(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> None:
    """注入 L1 上下文到 LLM 请求（内部函数）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    # 1. 获取 L1Buffer 组件
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.debug("L1 Buffer 组件不可用，跳过上下文注入")
        return
    
    # 类型转换：get_component 返回 Component，实际为 L1Buffer
    l1_buffer = cast("L1Buffer", buffer)
    
    # 2. 获取群聊ID
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    
    # 3. 获取配置中的最大消息条数
    # TODO: 从 component_manager 获取配置
    # 暂时使用默认值
    max_length = 20
    
    # 4. 获取上下文消息
    messages = l1_buffer.get_context(group_id, max_length)
    if not messages:
        logger.debug(f"群聊 {group_id} 的 L1 上下文为空，跳过注入")
        return
    
    # 5. 转换为 OpenAI Chat API 格式
    context_list = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]
    
    # 6. 注入到 req.contexts
    if req.contexts:
        req.contexts = context_list + req.contexts
    else:
        req.contexts = context_list
    
    logger.debug(f"已注入 {len(messages)} 条 L1 上下文消息到群聊 {group_id}")


async def _inject_user_profile(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> None:
    """注入用户画像到 LLM 请求（内部函数）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    # 1. 检查是否启用自动注入
    from iris_memory.config import get_config
    config = get_config()
    if not config.get("profile.enable"):
        return
    
    # 检查是否启用自动注入配置（如果配置项存在）
    enable_auto_injection = config.get("profile.enable_auto_injection")
    if enable_auto_injection is not None and not enable_auto_injection:
        return
    
    # 2. 获取 ProfileStorage 组件
    profile_storage = component_manager.get_component("profile")
    if not profile_storage or not profile_storage.is_available:
        logger.debug("画像系统组件不可用，跳过画像注入")
        return
    
    # 3. 获取群聊ID和用户ID
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    if not user_id:
        logger.debug("无法获取用户ID，跳过画像注入")
        return
    
    # 4. 根据群聊隔离配置决定 group_id
    effective_group_id = group_id if config.get("isolation_config.enable_group_isolation") else "default"
    
    # 5. 获取画像
    from iris_memory.profile import GroupProfileManager, UserProfileManager
    
    group_manager = GroupProfileManager(profile_storage)
    user_manager = UserProfileManager(profile_storage)
    
    # 获取群聊画像和用户画像
    group_profile = await group_manager.get_or_create(group_id)
    user_profile = await user_manager.get_or_create(user_id, effective_group_id)
    
    # 6. 格式化并注入到 system_prompt
    profile_text = _format_profiles_for_injection(group_profile, user_profile)
    
    if profile_text:
        # 注入到 system_prompt
        if req.prompt:
            req.prompt = profile_text + "\n\n" + req.prompt
        else:
            req.prompt = profile_text
        
        logger.debug(f"已注入画像信息到群聊 {group_id} 用户 {user_id}")


def _format_profiles_for_injection(
    group_profile: "GroupProfile",
    user_profile: "UserProfile"
) -> str:
    """格式化画像为注入文本
    
    Args:
        group_profile: 群聊画像对象
        user_profile: 用户画像对象
    
    Returns:
        格式化的画像文本
    """
    lines = ["[画像信息]"]
    
    # 群聊画像
    if group_profile.current_topic:
        lines.append(f"群聊当前话题: {group_profile.current_topic}")
    
    if group_profile.interests:
        lines.append(f"群聊兴趣: {', '.join(group_profile.interests[:5])}")
    
    if group_profile.atmosphere_tags:
        lines.append(f"群聊氛围: {', '.join(group_profile.atmosphere_tags)}")
    
    if group_profile.blacklist_topics:
        lines.append(f"⚠️ 禁忌话题: {', '.join(group_profile.blacklist_topics)}")
    
    lines.append("")
    
    # 用户画像
    if user_profile.user_name:
        lines.append(f"用户昵称: {user_profile.user_name}")
    
    if user_profile.current_emotional_state:
        lines.append(f"用户当前情绪: {user_profile.current_emotional_state}")
    
    if user_profile.personality_tags:
        lines.append(f"用户性格: {', '.join(user_profile.personality_tags)}")
    
    if user_profile.interests:
        lines.append(f"用户兴趣: {', '.join(user_profile.interests[:5])}")
    
    if user_profile.bot_relationship:
        lines.append(f"用户对你的称呼: {user_profile.bot_relationship}")
    
    if user_profile.taboo_topics:
        lines.append(f"⚠️ 用户禁忌话题: {', '.join(user_profile.taboo_topics)}")
    
    return chr(10).join(lines)


async def _parse_images_if_related_mode(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> None:
    """解析图片并入队 L1 Buffer（related 模式）
    
    仅在 related 模式下解析相关图片。
    all 模式已在消息钩子中处理。
    
    相关图片包括：
    - 触发 LLM 的消息中的图片
    - 触发 LLM 的消息所引用/回复的消息中的图片
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    # 1. 检查是否启用图片解析
    from iris_memory.config import get_config
    config = get_config()
    if not config.get("image_parsing.enable"):
        return
    
    # 2. 获取解析模式
    mode = config.get("image_parsing.parsing_mode", "related")
    
    # 3. 如果是 all 模式，不做任何事（已在消息钩子中处理）
    if mode == "all":
        return
    
    # 4. related 模式：解析相关图片
    if mode != "related":
        logger.warning(f"未知的图片解析模式：{mode}")
        return
    
    # 5. 从平台适配器获取图片列表
    adapter = get_adapter(event)
    images = adapter.get_images(event)
    
    if not images:
        logger.debug("消息中无图片，跳过解析")
        return
    
    # 6. 获取 ImageQuotaManager 组件
    quota_manager = component_manager.get_component("image_quota")
    if not quota_manager or not quota_manager.is_available:
        logger.debug("图片解析配额管理器不可用，跳过解析")
        return
    
    # 7. 检查配额
    has_quota = await quota_manager.check_quota()
    if not has_quota:
        logger.info("图片解析配额已耗尽，跳过解析")
        return
    
    # 8. 使用配额
    quota_used = await quota_manager.use_quota(len(images))
    if not quota_used:
        logger.warning("图片解析配额使用失败")
        return
    
    # 9. 获取 LLMManager 组件
    llm_manager = component_manager.get_component("llm_manager")
    if not llm_manager or not llm_manager.is_available:
        logger.warning("LLM Manager 不可用，跳过图片解析")
        return
    
    # 10. 创建 ImageParser
    from iris_memory.image import ImageParser
    
    provider = config.get("image_parsing.provider", "")
    parser = ImageParser(llm_manager, provider)
    
    # 11. 解析图片
    logger.info(f"开始解析 {len(images)} 张图片（related 模式）")
    
    parse_results = await parser.parse_batch(images)
    
    # 12. 将解析结果入队 L1 Buffer
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.warning("L1 Buffer 不可用，无法入队图片解析结果")
        return
    
    l1_buffer = cast("L1Buffer", buffer)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    success_count = 0
    for result in parse_results:
        if not result.success:
            logger.warning(f"图片解析失败：{result.error_message}")
            continue
        
        if not result.content:
            logger.debug("图片解析结果为空，跳过入队")
            continue
        
        # 入队解析结果
        await l1_buffer.add_message(
            group_id=group_id,
            role="user",
            content=f"[图片内容] {result.content}",
            source=user_id
        )
        success_count += 1
    
    logger.info(f"已入队 {success_count}/{len(images)} 张图片的解析结果")
    
    # 13. 将图片解析结果追加到 req.contexts
    for result in parse_results:
        if result.success and result.content:
            if req.contexts is None:
                req.contexts = []
            req.contexts.append({
                "role": "user",
                "content": f"[图片内容] {result.content}"
            })
    
    if success_count > 0:
        logger.debug(f"已追加 {success_count} 条图片解析结果到 LLM 请求上下文")
