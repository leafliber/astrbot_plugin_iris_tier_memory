"""
Iris Tier Memory - 总结器

负责触发总结逻辑，调用 LLM 生成总结。
阶段 5：LLMManager 实现后，总结功能正式可用
"""

from typing import Optional, TYPE_CHECKING
import json
import re

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import ContextMessage, MessageQueue

if TYPE_CHECKING:
    from iris_memory.llm import LLMManager

logger = get_logger("summarizer")


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
        
        max_length = config.get("l1_buffer.inject_queue_length")
        if len(queue) >= max_length:
            logger.debug(
                f"队列长度 {len(queue)} >= {max_length}，触发总结"
            )
            return True
        
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
        
        将消息列表转换为总结提示词，要求 LLM 同时输出：
        1. 记忆总结（分条格式）
        2. 群聊画像分析
        3. 用户画像分析
        
        Args:
            messages: 消息列表
        
        Returns:
            总结提示词
        """
        formatted_messages = []
        user_names = set()
        
        for msg in messages:
            if msg.role == "user":
                user_name = msg.metadata.get("user_name") if msg.metadata else None
                if user_name:
                    formatted_messages.append(f"[{user_name}]: {msg.content}")
                    user_names.add(user_name)
                else:
                    formatted_messages.append(f"[用户]: {msg.content}")
            else:
                formatted_messages.append(f"[助手]: {msg.content}")
        
        messages_text = "\n".join(formatted_messages)
        user_names_list = list(user_names) if user_names else ["未知用户"]
        
        prompt = f"""请分析以下对话，提取记忆信息并分析画像特征。

对话内容：
{messages_text}

## 任务一：提取记忆信息

### 提取标准（必须同时满足）
1. **信息价值**：包含用户偏好、重要事实、计划安排、观点态度、技能经验等可复用信息
2. **独立完整**：脱离上下文也能理解其含义
3. **非即时性**：不是仅在当前对话中有意义

### 排除以下内容
- 寒暄客套（你好、谢谢、不客气、再见等）
- 简短回复（好的、嗯、哦、知道了、明白等）
- 纯粹的问题（不含信息的问题本身不记录）
- 即时性指令（如"请帮我查一下"、"翻译这段话"等一次性请求）
- 情绪表达（哈哈、无语、生气等纯情绪词）
- 确认性回复（收到、已读、好的收到等）

## 任务二：分析群聊画像

从对话中分析群聊整体特征：
- interests: 群聊兴趣点（多次出现的话题）
- atmosphere_tags: 氛围标签（轻松、严肃、技术范、娱乐等）
- common_expressions: 常用语/群内梗

## 任务三：分析用户画像

为参与对话的用户分析个人特征：
- emotional_state: 当前情感状态
- personality_tags: 性格标签（外向、内向、幽默、理性等）
- interests: 兴趣爱好
- language_style: 语言风格（简洁、详细、正式、随意等）

## 输出格式

请严格按照以下 JSON 格式输出：

```json
{{
  "memories": [
    "- 张三正在学习Python，觉得装饰器概念较难理解",
    "- 李四下周三要去北京出差，周日返回"
  ],
  "group_profile": {{
    "interests": ["Python学习", "出差安排"],
    "atmosphere_tags": ["轻松", "互助"],
    "common_expressions": []
  }},
  "user_profiles": {{
    "张三": {{
      "emotional_state": "困惑但积极",
      "personality_tags": ["好学"],
      "interests": ["Python编程"],
      "language_style": "简洁"
    }},
    "李四": {{
      "emotional_state": "平静",
      "personality_tags": ["热心"],
      "interests": [],
      "language_style": "简洁"
    }}
  }}
}}
```

## 注意事项
1. 如果没有有效记忆，memories 数组为空
2. 如果无法分析出某个画像字段，该字段留空数组或空字符串
3. 仅输出 JSON，不要添加任何其他内容
4. 对话中出现的用户：{', '.join(user_names_list)}

请分析并输出 JSON："""
        
        return prompt


def parse_summary_response(response: str) -> dict:
    """解析总结响应
    
    从 LLM 响应中提取 JSON 内容。
    
    Args:
        response: LLM 响应文本
    
    Returns:
        解析后的字典，包含：
        - memories: 记忆列表
        - group_profile: 群聊画像
        - user_profiles: 用户画像字典
    """
    result = {
        "memories": [],
        "group_profile": {},
        "user_profiles": {}
    }
    
    if not response:
        return result
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            parsed = json.loads(json_match.group())
            
            if "memories" in parsed:
                result["memories"] = parsed["memories"]
            
            if "group_profile" in parsed:
                result["group_profile"] = parsed["group_profile"]
            
            if "user_profiles" in parsed:
                result["user_profiles"] = parsed["user_profiles"]
            
            return result
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败: {e}")
    
    lines = response.strip().split('\n')
    memories = []
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            memories.append(line)
    
    if memories:
        result["memories"] = memories
    
    return result


def format_memories_for_l2(memories: list[str]) -> str:
    """将记忆列表格式化为 L2 写入格式
    
    Args:
        memories: 记忆列表
    
    Returns:
        格式化的记忆文本
    """
    if not memories:
        return ""
    return '\n'.join(memories)
