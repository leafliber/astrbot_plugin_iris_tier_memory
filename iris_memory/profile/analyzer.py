"""
Iris Tier Memory - 画像分析器

使用规则 + LLM 混合策略分析画像特征。
短期字段使用规则匹配（无LLM），中长期字段使用LLM分析。
"""

from typing import List, Dict, Optional, Union, TYPE_CHECKING
import json

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import UpdateTier

if TYPE_CHECKING:
    from iris_memory.llm import LLMManager

logger = get_logger("profile")


EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "愉快": ["哈哈", "嘻嘻", "开心", "高兴", "快乐", "太好了", "好耶", "棒", "赞", "喜欢", "爱", "幸福", "😄", "😊", "🎉", "😂", "🤣"],
    "兴奋": ["太棒了", "太强了", "厉害", "牛", "绝了", "yyds", "冲", "燃", "🔥", "💪", "🚀"],
    "困惑": ["不懂", "不理解", "什么意思", "为什么", "怎么回事", "迷茫", "困惑", "❓", "🤔"],
    "沮丧": ["唉", "难过", "伤心", "失望", "郁闷", "烦", "累", "无语", "😔", "😢", "😭"],
    "愤怒": ["生气", "愤怒", "烦死了", "气死", "可恶", "讨厌", "😡", "🤬"],
    "焦虑": ["担心", "害怕", "焦虑", "紧张", "不安", "着急", "慌", "😰", "😟"],
    "平静": ["嗯", "好的", "了解", "明白", "知道了", "行", "可以", "哦"],
}

EMOTION_RULE_CONFIDENCE = 0.5
EMOTION_LLM_CONFIDENCE = 0.8


class ProfileAnalyzer:
    """画像分析器

    使用规则 + LLM 混合策略分析画像特征。
    短期字段（情感状态等）使用规则匹配，无需LLM调用。
    中期字段使用轻量LLM分析。
    长期字段使用深度LLM分析，要求高置信度。

    Attributes:
        _llm_manager: LLM 调用管理器实例
    """

    def __init__(self, llm_manager: "LLMManager"):
        self._llm_manager = llm_manager

    def detect_emotional_state(self, messages: List[str]) -> tuple[str, float]:
        """规则检测情感状态（无需LLM）

        通过关键词匹配检测消息中的情感倾向。
        返回 (情感状态, 置信度)。

        Args:
            messages: 近期对话消息列表

        Returns:
            (情感状态字符串, 置信度0.0~1.0)
        """
        if not messages:
            return "", 0.0

        emotion_scores: Dict[str, int] = {}
        total_matches = 0

        for msg in messages:
            for emotion, keywords in EMOTION_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in msg:
                        emotion_scores[emotion] = emotion_scores.get(emotion, 0) + 1
                        total_matches += 1
                        break

        if not emotion_scores:
            return "", 0.0

        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        match_ratio = emotion_scores[dominant_emotion] / max(len(messages), 1)

        if match_ratio >= 0.5:
            confidence = EMOTION_RULE_CONFIDENCE + 0.2
        elif match_ratio >= 0.3:
            confidence = EMOTION_RULE_CONFIDENCE + 0.1
        else:
            confidence = EMOTION_RULE_CONFIDENCE

        return dominant_emotion, min(confidence, 0.9)

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
        if tier == UpdateTier.SHORT:
            return self._analyze_group_short(messages)

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
        if tier == UpdateTier.SHORT:
            return self._analyze_user_short(messages)

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

    def _analyze_group_short(self, messages: List[str]) -> Dict[str, List[str]]:
        """群聊画像短期分析（规则，无LLM）

        Args:
            messages: 近期对话消息列表

        Returns:
            短期分析结果
        """
        return {}

    def _analyze_user_short(self, messages: List[str]) -> Dict[str, str]:
        """用户画像短期分析（规则，无LLM）

        仅检测情感状态，无需LLM。

        Args:
            messages: 用户近期对话列表

        Returns:
            短期分析结果
        """
        emotion, confidence = self.detect_emotional_state(messages)
        if emotion:
            return {"emotional_state": emotion, "emotional_confidence": str(confidence)}
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
            max_messages = config.get("profile_max_messages_for_analysis") if hasattr(config, 'get') else 50
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
    "common_expressions": ["常用语或群内梗"],
    "custom_fields": {{
        "自定义字段名": "字段值"
    }}
}}

注意：
1. 基于对话内容客观分析
2. 兴趣点应是多次出现的话题
3. 氛围标签描述群聊整体风格
4. 常用语应为群内特有的表达
5. custom_fields 用于存储额外有价值信息

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
1. 长期标签描述群聊的核心身份特征（如"技术交流群"、"游戏群"）
2. 禁忌话题是群内明确不宜讨论的内容
3. 只有确实发现变化时才更新 interests 和 atmosphere_tags
4. 宁可少标不要多标，长期标签必须高度可靠

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
            max_messages = config.get("profile_max_messages_for_analysis") if hasattr(config, 'get') else 30
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
1. 性格标签基于对话风格推断
2. 兴趣应从对话内容中识别
3. 语言风格描述用户的表达习惯
4. custom_fields 用于存储额外有价值信息（如职业背景、技能水平等）

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
2. occupation 仅在对话中有明确线索时填写
3. bot_relationship 仅在用户有明确称呼习惯时填写
4. important_events 只记录真正重要的事件（如工作变动、人生里程碑）
5. 只有确实发现变化时才更新 personality_tags 和 interests

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
