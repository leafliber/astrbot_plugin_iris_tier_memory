"""
LLM 请求钩子处理模块

负责处理 LLM 请求前的钩子逻辑，包括：
- L1 上下文注入
- 用户画像注入
- 图片解析（related 模式）
- 知识图谱检索结果注入（未来扩展）
"""
from typing import TYPE_CHECKING, List, cast

from iris_memory.core import get_logger

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
    2. L2 记忆注入（向量检索）
    3. L3 知识图谱注入（图谱检索 + 图增强）
    4. 用户画像注入
    5. 图片解析（related 模式）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    await _inject_l1_context(event, req, component_manager)
    l2_results = await _inject_l2_memory(event, req, component_manager)
    await _inject_l3_knowledge_graph(event, req, component_manager, l2_results)
    await _inject_user_profile(event, req, component_manager)
    await _parse_images_if_related_mode(event, req, component_manager)


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
    from iris_memory.platform import get_adapter
    
    buffer = component_manager.get_component("l1_buffer")
    if not buffer or not buffer.is_available:
        logger.debug("L1 Buffer 组件不可用，跳过上下文注入")
        return
    
    l1_buffer = cast("L1Buffer", buffer)
    
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    
    max_length = 20
    
    messages = l1_buffer.get_context(group_id, max_length)
    if not messages:
        logger.debug(f"群聊 {group_id} 的 L1 上下文为空，跳过注入")
        return
    
    context_list = []
    for msg in messages:
        content = msg.content
        if msg.role == "user":
            user_name = msg.metadata.get("user_name") if msg.metadata else None
            if user_name:
                content = f"[{user_name}]: {content}"
        context_list.append({"role": msg.role, "content": content})
    
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
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    
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


async def _inject_l2_memory(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> List["MemorySearchResult"]:
    """注入 L2 记忆到 LLM 请求（内部函数）
    
    执行 L2 向量检索并注入到上下文。
    
    流程：
    1. 检查 L2 是否启用
    2. 执行向量检索
    3. Token 预算控制
    4. 注入到 system_prompt
    5. 返回检索结果（供 L3 使用）
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    
    Returns:
        L2 检索结果列表
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    
    config = get_config()
    
    # 1. 检查是否启用 L2 记忆库
    if not config.get("l2_memory.enable"):
        logger.debug("L2 记忆库未启用，跳过记忆注入")
        return []
    
    # 2. 获取 L2MemoryAdapter 组件
    l2_adapter = component_manager.get_component("l2_memory")
    if not l2_adapter or not l2_adapter.is_available:
        logger.debug("L2 记忆库组件不可用，跳过记忆注入")
        return []
    
    # 3. 获取群聊ID和用户消息
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    
    # 提取用户消息作为查询文本
    query_text = ""
    if hasattr(event, 'message_str') and event.message_str:
        query_text = event.message_str
    elif hasattr(event, 'get_message_str'):
        query_text = event.get_message_str()
    
    if not query_text:
        logger.debug("无法获取用户消息，跳过记忆检索")
        return []
    
    try:
        # 4. 创建记忆检索器
        from iris_memory.l2_memory import MemoryRetriever
        
        retriever = MemoryRetriever(component_manager)
        
        # 5. 执行向量检索
        results = await retriever.retrieve(query_text, group_id)
        
        if not results:
            logger.debug("L2 检索未找到相关记忆")
            return []
        
        # 6. Token 预算控制
        from iris_memory.enhancement import TokenBudgetController
        
        budget_controller = TokenBudgetController()
        max_tokens = config.get("token_budget_max_tokens", 2000)
        
        trimmed_results, actual_tokens = budget_controller.trim_memories(
            memories=results,
            max_tokens=max_tokens
        )
        
        logger.debug(f"L2 检索到 {len(results)} 条记忆，裁剪后 {len(trimmed_results)} 条")
        
        # 7. 格式化并注入到 system_prompt
        memory_text = _format_l2_memories_for_injection(trimmed_results)
        
        if memory_text:
            if req.prompt:
                req.prompt = memory_text + "\n\n" + req.prompt
            else:
                req.prompt = memory_text
            
            logger.debug(f"已注入 L2 记忆到群聊 {group_id}")
        
        return trimmed_results
    
    except Exception as e:
        logger.error(f"L2 记忆注入失败: {e}", exc_info=True)
        return []


async def _inject_l3_knowledge_graph(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager",
    l2_results: List["MemorySearchResult"]
) -> None:
    """注入 L3 知识图谱到 LLM 请求（内部函数）
    
    执行图谱检索并注入到上下文，支持两种互补模式：
    
    1. 图增强模式（推荐）：
       - 基于用户查询文本在图谱中搜索相关节点
       - 使用关键词提取 + 多跳路径扩展
       - 配置项：l2_memory.enable_graph_enhancement
    
    2. 纯图谱检索模式（补充）：
       - 基于 L2 记忆关联的图谱节点 ID 进行路径扩展
       - 需要记忆在写入时记录 kg_node_id 等元数据
       - 自动执行（当 L2 结果包含节点 ID 时）
    
    两种模式可以共存，产生的图谱上下文会合并注入。
    
    流程：
    1. 检查 L3 是否启用
    2. 执行图谱检索（图增强 + 纯图谱检索）
    3. 合并并格式化图谱上下文
    4. 注入到 system_prompt
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
        l2_results: L2 检索结果（用于图增强和纯图谱检索）
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    
    config = get_config()
    
    # 1. 检查是否启用 L3 知识图谱
    if not config.get("l3_kg.enable"):
        logger.debug("L3 知识图谱未启用，跳过图谱注入")
        return
    
    # 2. 获取 L3KGAdapter 组件
    kg_adapter = component_manager.get_component("l3_kg")
    if not kg_adapter or not kg_adapter.is_available:
        logger.debug("L3 知识图谱组件不可用，跳过图谱注入")
        return
    
    # 3. 获取群聊ID、用户ID和用户消息
    adapter = get_adapter(event)
    group_id = adapter.get_group_id(event)
    user_id = adapter.get_user_id(event)
    
    # 提取用户消息作为查询文本（用于图增强）
    query_text = ""
    if hasattr(event, 'message_str') and event.message_str:
        query_text = event.message_str
    elif hasattr(event, 'get_message_str'):
        query_text = event.get_message_str()
    
    try:
        # 4. 图谱检索逻辑
        enable_graph_enhancement = config.get("l2_memory.enable_graph_enhancement", False)
        graph_contexts: List[str] = []  # 收集图谱上下文
        memory_node_ids: List[str] = []  # 收集记忆节点 ID
        
        # 4.1 从 L2 结果中提取节点 ID（用于两种模式）
        if l2_results:
            for result in l2_results:
                metadata = result.entry.metadata
                node_id = metadata.get("memory_node_id") or \
                          metadata.get("kg_node_id") or \
                          metadata.get("node_id") or \
                          metadata.get("entity_id")
                if node_id:
                    memory_node_ids.append(node_id)
        
        # 4.2 图增强模式：基于查询文本 + 节点 ID + 用户 ID 扩展
        if enable_graph_enhancement:
            from iris_memory.enhancement import GraphEnhancer
            
            enhancer = GraphEnhancer(component_manager)
            enhanced_results, graph_context = await enhancer.enhance(
                memories=l2_results,
                group_id=group_id,
                query=query_text,
                node_ids=memory_node_ids,  # 传入节点 ID
                user_id=user_id  # 传入用户 ID
            )
            
            if graph_context:
                graph_contexts.append(graph_context)
                logger.debug(f"图增强检索完成（关键词 + {len(memory_node_ids)} 个节点 + 用户 {user_id}）")
        
        # 4.3 纯图谱检索模式：仅基于节点 ID 扩展（当图增强未启用时）
        elif memory_node_ids:
            from iris_memory.l3_kg import GraphRetriever
            
            retriever = GraphRetriever(kg_adapter)
            
            # 基于记忆节点进行路径扩展
            nodes, edges = await retriever.retrieve_with_expansion(
                memory_node_ids=memory_node_ids,
                group_id=group_id
            )
            
            if nodes or edges:
                # 格式化图谱结果
                graph_text = retriever.format_for_context(nodes, edges)
                
                if graph_text:
                    graph_contexts.append(graph_text)
                    logger.debug(f"纯图谱检索完成（基于 {len(memory_node_ids)} 个记忆节点）")
        
        # 4.4 注入所有图谱上下文
        if graph_contexts:
            combined_context = "\n\n".join(graph_contexts)
            if req.prompt:
                req.prompt = combined_context + "\n\n" + req.prompt
            else:
                req.prompt = combined_context
            
            logger.info(f"已注入图谱上下文到群聊 {group_id}（共 {len(graph_contexts)} 部分）")
    
    except Exception as e:
        logger.error(f"L3 知识图谱注入失败: {e}", exc_info=True)


def _format_l2_memories_for_injection(
    memories: List["MemorySearchResult"]
) -> str:
    """格式化 L2 记忆为注入文本
    
    Args:
        memories: L2 记忆检索结果列表
    
    Returns:
        格式化的记忆文本
    """
    if not memories:
        return ""
    
    lines = ["[历史记忆]"]
    
    for i, memory in enumerate(memories, 1):
        # 添加记忆内容
        lines.append(f"{i}. {memory.entry.content}")
        
        # 可选：添加置信度（如果足够高）
        if memory.entry.confidence and memory.entry.confidence > 0.9:
            lines.append(f"   （置信度：{memory.entry.confidence:.2f}）")
    
    return chr(10).join(lines)


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
    """解析图片并注入 LLM 上下文（related 模式）
    
    仅在 related 模式下解析 L1 Buffer 范围内的图片。
    all 模式已在消息钩子中处理。
    
    流程：
    1. 获取 L1Buffer 图片队列中的待解析图片
    2. 检查缓存，过滤已解析的图片
    3. 批量解析（并发控制、数量限制）
    4. 结果存入缓存
    5. 注入 LLM 上下文
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    from iris_memory.config import get_config
    from iris_memory.platform import get_adapter
    from iris_memory.image import ImageParser, ImageParseStatus, ImageParseCache
    import asyncio
    
    config = get_config()
    if not config.get("image_parsing.enable"):
        return
    
    mode = config.get("image_parsing.parsing_mode", "related")
    
    if mode == "all":
        return
    
    if mode != "related":
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
    max_concurrent = config.get("image_parsing.max_concurrent_parse", 3)
    
    pending_images = l1_buffer.get_images(group_id, limit=max_parse, only_pending=True)
    
    if not pending_images:
        return
    
    images_to_parse = []
    cached_results = []
    
    for img_item in pending_images:
        if cache_manager and cache_manager.is_available:
            cached = await cache_manager.get_cache(img_item.image_hash)
            if cached:
                l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.SUCCESS)
                cached_results.append((img_item, cached))
                continue
        
        images_to_parse.append(img_item)
    
    if cached_results:
        logger.debug(f"从缓存读取 {len(cached_results)} 条图片解析结果")
    
    if not images_to_parse:
        for img_item, cached in cached_results:
            if req.contexts is None:
                req.contexts = []
            req.contexts.append({
                "role": "user",
                "content": f"[图片内容] {cached.content}"
            })
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
    
    logger.info(f"开始解析 {len(images_to_parse)} 张图片（related 模式）")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def parse_with_semaphore(img_item):
        async with semaphore:
            if not img_item.image_info or not img_item.image_info.has_url:
                return (img_item, None)
            result = await parser.parse(img_item.image_info)
            return (img_item, result)
    
    parse_tasks = [parse_with_semaphore(img) for img in images_to_parse]
    parse_results = await asyncio.gather(*parse_tasks)
    
    success_count = 0
    for img_item, result in parse_results:
        if result is None:
            l1_buffer.mark_image_parsed(group_id, img_item.image_hash, ImageParseStatus.FAILED)
            continue
        
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
        
        if req.contexts is None:
            req.contexts = []
        req.contexts.append({
            "role": "user",
            "content": f"[图片内容] {result.content}"
        })
        
        success_count += 1
    
    for img_item, cached in cached_results:
        if req.contexts is None:
            req.contexts = []
        req.contexts.append({
            "role": "user",
            "content": f"[图片内容] {cached.content}"
        })
    
    total_injected = success_count + len(cached_results)
    if total_injected > 0:
        logger.info(
            f"已注入 {total_injected} 条图片解析结果到 LLM 上下文 "
            f"（新解析 {success_count}，缓存 {len(cached_results)}）"
        )
