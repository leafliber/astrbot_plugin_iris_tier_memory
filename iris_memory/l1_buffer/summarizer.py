"""
Iris Tier Memory - 总结器

负责触发总结逻辑，调用 LLM 生成总结。
阶段 5：LLMManager 实现后，总结功能正式可用
"""

from typing import Optional, TYPE_CHECKING

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import ContextMessage, MessageQueue

if TYPE_CHECKING:
    from iris_memory.llm import LLMManager

logger = get_logger("summarizer")


# ============================================================================
# 总结器类
# ============================================================================

class Summarizer:
    """消息总结器
    
    负责检查触发条件、调用 LLM 生成总结。
    
    Attributes:
        llm_manager: LLM 调用管理器实例
        provider: 总结使用的模型提供商
    
    Examples:
        >>> summarizer = Summarizer(llm_manager=llm_manager)
        >>> queue = MessageQueue(group_id="group_123")
        >>> await summarizer.summarize(queue)
    """
    
    def __init__(
        self,
        llm_manager: "LLMManager",
        provider: str = ""
    ):
        """初始化总结器
        
        Args:
            llm_manager: LLM 调用管理器实例
            provider: 总结使用的模型提供商（留空使用默认）
        """
        self.llm_manager = llm_manager
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
            >>> summarizer = Summarizer(llm_manager)
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
    
    async def summarize(
        self, 
        messages: list[ContextMessage]
    ) -> Optional[str]:
        """总结消息列表
        
        调用 LLM 生成消息的总结。
        
        Args:
            messages: 待总结的消息列表
        
        Returns:
            总结文本
        
        Raises:
            Exception: LLM 调用失败时抛出
        """
        if not messages:
            logger.debug("消息列表为空，跳过总结")
            return None
        
        try:
            total_tokens = sum(msg.token_count for msg in messages)
            prompt = self._build_summary_prompt(messages)
            
            logger.info(f"开始总结，共 {len(messages)} 条消息，{total_tokens} tokens")
            
            summary = await self.llm_manager.generate(
                prompt=prompt,
                module="l1_summarizer",
                provider_id=self.provider if self.provider else None
            )
            
            logger.info(f"总结完成，长度：{len(summary)} 字符")
            return summary
        
        except Exception as e:
            logger.error(f"总结失败：{e}", exc_info=True)
            raise
    
    def _build_summary_prompt(self, messages: list[ContextMessage]) -> str:
        """构建总结提示词
        
        将消息列表转换为总结提示词，要求 LLM 输出分条格式。
        
        Args:
            messages: 消息列表
        
        Returns:
            总结提示词
        """
        formatted_messages = []
        for msg in messages:
            if msg.role == "user":
                user_name = msg.metadata.get("user_name") if msg.metadata else None
                if user_name:
                    formatted_messages.append(f"[{user_name}]: {msg.content}")
                else:
                    formatted_messages.append(f"[用户]: {msg.content}")
            else:
                formatted_messages.append(f"[助手]: {msg.content}")
        
        messages_text = "\n".join(formatted_messages)
        
        prompt = f"""请从以下对话中提取有价值的长期记忆信息。

对话内容：
{messages_text}

## 提取标准（必须同时满足）
1. **信息价值**：包含用户偏好、重要事实、计划安排、观点态度、技能经验等可复用信息
2. **独立完整**：脱离上下文也能理解其含义
3. **非即时性**：不是仅在当前对话中有意义（如"好的"、"谢谢"、"知道了"等不记录）

## 排除以下内容
- 寒暄客套（你好、谢谢、不客气、再见等）
- 简短回复（好的、嗯、哦、知道了、明白等）
- 纯粹的问题（不含信息的问题本身不记录）
- 即时性指令（如"请帮我查一下"、"翻译这段话"等一次性请求）
- 情绪表达（哈哈、无语、生气等纯情绪词）
- 确认性回复（收到、已读、好的收到等）

## 输出格式
每条记忆独立成行，使用 "- " 开头，格式：`- [用户名] + 具体信息内容`

## 示例
对话：
[张三]: 你好
[助手]: 你好！有什么可以帮你的？
[张三]: 我最近在学习Python，感觉装饰器有点难理解
[李四]: @张三 推荐你看官方文档的装饰器章节
[张三]: 好的谢谢
[李四]: 对了，我下周要去北京出差
[张三]: 哪天去？
[李四]: 周三出发，周日回来

输出：
- 张三正在学习Python，觉得装饰器概念较难理解
- 李四推荐张三阅读Python官方文档的装饰器章节
- 李四下周三要去北京出差，周日返回

请提取有价值的记忆信息（无有效信息则输出"无"）："""
        
        return prompt
