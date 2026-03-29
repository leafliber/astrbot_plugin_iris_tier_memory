"""
LLM 请求钩子处理模块

负责处理 LLM 请求前的钩子逻辑，包括：
- L1 上下文注入
- 用户画像注入
- 知识图谱检索结果注入（未来扩展）
"""
from typing import TYPE_CHECKING, cast

from iris_memory.core import get_logger
from iris_memory.platform import get_adapter
from iris_memory.config import get_config

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
    3. TODO: 知识图谱检索结果注入（阶段 4）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    await _inject_l1_context(event, req, component_manager)
    await _inject_user_profile(event, req, component_manager)
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
