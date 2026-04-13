"""
Iris Tier Memory - 画像分析器

使用 LLM 分析画像特征。
仅保留中长期字段分析。
"""

from typing import List, Dict, Optional, Union, TYPE_CHECKING
import json

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import UpdateTier

if TYPE_CHECKING:
    from iris_memory.llm import LLMManager

logger = get_logger("profile")


class ProfileAnalyzer:
    """画像分析器

    使用 LLM 分析画像特征。
    仅保留中长期字段分析。

    Attributes:
        _llm_manager: LLM 调用管理器实例
    """

    def __init__(self, llm_manager: "LLMManager"):
        self._llm_manager = llm_manager

    async def analyze_group_profile(
        self,
        messages: List[str],
        current_profile: Dict,
        tier: UpdateTier = UpdateTier.MID
    ) -> Dict[str, List[str]]:
        """分析群聊画像

        Args:
            messages: 近期对话消息列表
            current_profile: 当前画像数据（字典格式）
            tier: 更新层级，决定分析深度

        Returns:
            分析结果字典
        """
        prompt = self._build_group_analysis_prompt(messages, current_profile, tier)

        try:
            response = await self._llm_manager.generate(
                prompt=prompt,
                module="profile_analysis"
            )

            result = self._parse_json_response(response)
            logger.info(f"群聊画像分析完成 (tier={tier.value})")
            return result

        except Exception as e:
            logger.error(f"群聊画像分析失败: {e}")
            return {}

    async def analyze_user_profile(
        self,
        messages: List[str],
        current_profile: Dict,
        tier: UpdateTier = UpdateTier.MID
    ) -> Dict[str, Union[str, List[str]]]:
        """分析用户画像

        Args:
            messages: 用户近期对话列表
            current_profile: 当前画像数据（字典格式）
            tier: 更新层级，决定分析深度

        Returns:
            分析结果字典
        """
        prompt = self._build_user_analysis_prompt(messages, current_profile, tier)

        try:
            response = await self._llm_manager.generate(
                prompt=prompt,
                module="profile_analysis"
            )

            result = self._parse_json_response(response)
            logger.info(f"用户画像分析完成 (tier={tier.value})")
            return result

        except Exception as e:
            logger.error(f"用户画像分析失败: {e}")
            return {}

    def _build_group_analysis_prompt(
        self,
        messages: List[str],
        current_profile: Dict,
        tier: UpdateTier = UpdateTier.MID
    ) -> str:
        """构建群聊画像分析 prompt

        Args:
            messages: 对话消息列表
            current_profile: 当前画像数据
            tier: 更新层级

        Returns:
            分析提示词
        """
        try:
            config = get_config()
            max_messages = config.get("profile_max_messages_for_analysis", 50)
        except RuntimeError:
            max_messages = 50
        limited_messages = messages[:max_messages]

        if tier == UpdateTier.LONG:
            return self._build_group_long_prompt(limited_messages, current_profile)

        return f"""分析以下群聊对话，提取群聊画像特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

近期对话：
{chr(10).join(limited_messages)}

请分析并返回JSON格式结果：
{{
    "interests": ["群聊兴趣点1", "兴趣点2"],
    "atmosphere_tags": ["氛围标签1", "标签2"],
    "custom_fields": {{
        "自定义字段名": "字段值"
    }}
}}

注意：
1. 基于对话内容客观分析
2. 兴趣点应是多次出现的话题，最多5个
3. 氛围标签描述群聊整体风格，最多3个
4. custom_fields 用于存储额外有价值信息
5. 不确定或无法判断的字段返回空数组

仅返回JSON，不要其他内容。"""

    def _build_group_long_prompt(
        self,
        messages: List[str],
        current_profile: Dict
    ) -> str:
        """构建群聊画像长期分析 prompt

        长期分析更关注核心特征和禁忌话题。

        Args:
            messages: 对话消息列表
            current_profile: 当前画像数据

        Returns:
            长期分析提示词
        """
        return f"""深度分析以下群聊对话，提取群聊的核心长期特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

近期对话：
{chr(10).join(messages)}

请分析并返回JSON格式结果：
{{
    "long_term_tags": ["核心特征标签1", "标签2"],
    "blacklist_topics": ["禁忌话题1", "话题2"],
    "interests": ["兴趣点（如有变化）"],
    "atmosphere_tags": ["氛围标签（如有变化）"],
    "custom_fields": {{
        "自定义字段名": "字段值"
    }}
}}

注意：
1. 长期标签描述群聊的核心身份特征（如"技术交流群"、"游戏群"），最多3个
2. 禁忌话题是群内明确不宜讨论的内容，必须非常确定才填写
3. 只有确实发现显著变化时才更新 interests 和 atmosphere_tags
4. 宁可少标不要多标，长期特征必须高度可靠
5. 不确定或无法判断的字段返回空数组

仅返回JSON，不要其他内容。"""

    def _build_user_analysis_prompt(
        self,
        messages: List[str],
        current_profile: Dict,
        tier: UpdateTier = UpdateTier.MID
    ) -> str:
        """构建用户画像分析 prompt

        Args:
            messages: 用户对话列表
            current_profile: 当前画像数据
            tier: 更新层级

        Returns:
            分析提示词
        """
        try:
            config = get_config()
            max_messages = config.get("profile_max_messages_for_analysis", 30)
        except RuntimeError:
            max_messages = 30
        limited_messages = messages[:max_messages]

        if tier == UpdateTier.LONG:
            return self._build_user_long_prompt(limited_messages, current_profile)

        return f"""分析以下用户对话，提取用户画像特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

用户近期对话：
{chr(10).join(limited_messages)}

请分析并返回JSON格式结果：
{{
    "personality_tags": ["性格标签1", "标签2"],
    "interests": ["兴趣1", "兴趣2"],
    "language_style": "语言风格描述",
    "custom_fields": {{
        "自定义字段名": "字段值"
    }}
}}

注意：
1. 性格标签基于对话风格推断，最多3个标签
2. 兴趣应从对话内容中识别，最多5个
3. 语言风格描述用户的表达习惯（如"简洁"、"幽默"、"正式"）
4. custom_fields 用于存储额外有价值信息
5. 不确定或无法判断的字段返回空数组或空字符串

仅返回JSON，不要其他内容。"""

    def _build_user_long_prompt(
        self,
        messages: List[str],
        current_profile: Dict
    ) -> str:
        """构建用户画像长期分析 prompt

        长期分析更关注职业、关系、重要事件等稳定特征。

        Args:
            messages: 用户对话列表
            current_profile: 当前画像数据

        Returns:
            长期分析提示词
        """
        return f"""深度分析以下用户对话，提取用户的长期稳定特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

用户近期对话：
{chr(10).join(messages)}

请分析并返回JSON格式结果：
{{
    "occupation": "职业/身份（如能判断）",
    "bot_relationship": "用户对AI助手的称呼或关系设定（如能判断）",
    "important_events": ["重要事件1", "事件2"],
    "taboo_topics": ["禁忌话题1"],
    "important_dates": [{{"date": "日期", "description": "描述"}}],
    "personality_tags": ["性格标签（如有变化）"],
    "interests": ["兴趣（如有变化）"],
    "custom_fields": {{
        "自定义字段名": "字段值"
    }}
}}

注意：
1. 长期特征必须高度可靠，宁可留空不要猜测
2. occupation 仅在对话中有明确线索时填写（如提到"今天加班写代码"）
3. bot_relationship 仅在用户有明确称呼习惯时填写（如"小助手"、"老师"）
4. important_events 只记录真正重要的事件（如工作变动、人生里程碑），最多5个
5. 只有确实发现显著变化时才更新 personality_tags 和 interests
6. 不确定或无法判断的字段返回空数组或空字符串

仅返回JSON，不要其他内容。"""

    def _parse_json_response(self, response: str) -> Dict:
        """解析 JSON 响应

        尝试从 LLM 响应中提取 JSON 内容。

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，失败返回空字典
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            logger.warning(f"无法解析JSON响应: {response[:100]}")
            return {}
