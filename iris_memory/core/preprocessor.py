"""
LLM 对话前处理模块

负责在 LLM 对话前执行各种预处理逻辑，包括：
- L1 上下文注入（当前实现）
- 用户画像注入（未来扩展）
- 知识图谱检索结果注入（未来扩展）
- 其他对话前处理逻辑
"""
from typing import TYPE_CHECKING, cast

from iris_memory.core import get_logger
from iris_memory.platform import get_adapter

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent
    from astrbot.api.provider import ProviderRequest
    from iris_memory.core.components import ComponentManager
    from iris_memory.l1_buffer import L1Buffer

logger = get_logger("preprocessor")


async def preprocess_llm_request(
    event: "AstrMessageEvent",
    req: "ProviderRequest",
    component_manager: "ComponentManager"
) -> None:
    """LLM 对话前处理主入口
    
    执行所有 LLM 对话前的预处理逻辑（按顺序执行）：
    1. L1 上下文注入
    2. TODO: 用户画像注入（阶段 9）
    3. TODO: 知识图谱检索结果注入（阶段 4）
    4. TODO: 其他对话前处理逻辑
    
    Args:
        event: AstrBot 消息事件对象
        req: LLM 提供者请求对象
        component_manager: 组件管理器实例
    """
    await _inject_l1_context(event, req, component_manager)
    # TODO: 在未来阶段添加其他预处理逻辑
    # await _inject_user_profile(event, req, component_manager)
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
