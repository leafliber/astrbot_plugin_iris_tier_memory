"""
Iris Tier Memory - 总结器

负责触发总结逻辑，调用 LLM 生成总结。
阶段 2-4：预留接口，总结功能不可用
阶段 5：LLMManager 实现后，总结功能正式可用
"""

from typing import Optional

from iris_memory.core import get_logger
from iris_memory.llm.caller import LLMCaller, PlaceholderLLMCaller
from iris_memory.config import get_config
from .models import ContextMessage, MessageQueue

logger = get_logger("summarizer")


# ============================================================================
# 总结器类
# ============================================================================

class Summarizer:
    """消息总结器
    
    负责检查触发条件、调用 LLM 生成总结。
    
    Attributes:
        llm_caller: LLM 调用器实例
        provider: 总结使用的模型提供商
    
    Examples:
        >>> from iris_memory.llm.caller import PlaceholderLLMCaller
        >>> summarizer = Summarizer(llm_caller=PlaceholderLLMCaller())
        >>> queue = MessageQueue(group_id="group_123")
        >>> await summarizer.summarize(queue)
        None  # 阶段 2-4 返回 None
    """
    
    def __init__(
        self,
        llm_caller: Optional[LLMCaller] = None,
        provider: str = ""
    ):
        """初始化总结器
        
        Args:
            llm_caller: LLM 调用器实例（可选，默认使用占位实现）
            provider: 总结使用的模型提供商（留空使用默认）
        """
        self.llm_caller = llm_caller or PlaceholderLLMCaller()
        self.provider = provider
        logger.info("总结器已初始化")
    
    def should_summarize(self, queue: MessageQueue) -> bool:
        """检查是否应该触发总结
        
        检查消息数量或 Token 数是否超过限制。
        
        Args:
            queue: 消息队列
        
        Returns:
            是否应该触发总结
        
        Examples:
            >>> queue = MessageQueue(group_id="group_123")
            >>> queue.total_tokens = 5000  # 超过默认限制 4000
            >>> summarizer = Summarizer()
            >>> summarizer.should_summarize(queue)
            True
        """
        config = get_config()
        
        # 检查消息数量
        max_length = config.get("l1_buffer.inject_queue_length")
        if len(queue) >= max_length:
            logger.debug(
                f"队列长度 {len(queue)} >= {max_length}，触发总结"
            )
            return True
        
        # 检查 Token 数量
        max_tokens = config.get("l1_buffer.max_queue_tokens")
        if queue.total_tokens >= max_tokens:
            logger.debug(
                f"队列 Token 数 {queue.total_tokens} >= {max_tokens}，触发总结"
            )
            return True
        
        return False
    
    async def summarize(self, queue: MessageQueue) -> Optional[str]:
        """总结队列消息
        
        调用 LLM 生成消息队列的总结。
        
        阶段 2-4：返回 None，不执行总结
        阶段 5：调用 LLM 生成总结
        
        Args:
            queue: 消息队列
        
        Returns:
            总结文本（阶段 2-4 返回 None）
        
        Raises:
            Exception: LLM 调用失败时抛出（阶段 5 后）
        """
        if queue.is_empty():
            logger.debug("队列为空，跳过总结")
            return None
        
        try:
            # 构建总结提示词
            messages = queue.to_message_list()
            prompt = self._build_summary_prompt(messages)
            
            logger.info(f"开始总结队列，共 {len(queue)} 条消息，{queue.total_tokens} tokens")
            
            # 调用 LLM（阶段 2-4 会抛出 NotImplementedError）
            summary = await self.llm_caller.call(prompt, self.provider)
            
            logger.info(f"总结完成，长度：{len(summary)} 字符")
            return summary
        
        except NotImplementedError:
            # 阶段 2-4：总结功能不可用，仅清空队列
            logger.warning(
                "总结功能尚未实现（阶段 5 完成），队列将被清空而不生成总结"
            )
            return None
        
        except Exception as e:
            logger.error(f"总结失败：{e}", exc_info=True)
            raise
    
    def _build_summary_prompt(self, messages: list[dict]) -> str:
        """构建总结提示词
        
        将消息列表转换为总结提示词。
        
        Args:
            messages: 消息列表
        
        Returns:
            总结提示词
        """
        # 格式化消息
        formatted_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            formatted_messages.append(f"{role}: {content}")
        
        messages_text = "\n".join(formatted_messages)
        
        # 构建提示词
        prompt = f"""请总结以下对话内容，提取关键信息：

{messages_text}

总结："""
        
        return prompt
