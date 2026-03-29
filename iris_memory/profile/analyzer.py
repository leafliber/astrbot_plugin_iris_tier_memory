"""
Iris Tier Memory - 画像分析器

使用 LLM 批量分析画像特征。
"""

from typing import List, Dict, TYPE_CHECKING
import json

from iris_memory.core import get_logger
from iris_memory.config import get_config

if TYPE_CHECKING:
    from iris_memory.llm import LLMManager

logger = get_logger("profile")


# ============================================================================
# 画像分析器
# ============================================================================

class ProfileAnalyzer:
    """画像分析器
    
    使用 LLM 分析对话内容，提取画像特征。
    支持群聊画像和用户画像的分析。
    
    Attributes:
        _llm_manager: LLM 调用管理器实例
    
    Examples:
        >>> analyzer = ProfileAnalyzer(llm_manager)
        >>> result = await analyzer.analyze_group_profile(messages, current_profile)
        >>> print(result["interests"])
        ['技术', 'AI']
    """
    
    def __init__(self, llm_manager: "LLMManager"):
        """初始化画像分析器
        
        Args:
            llm_manager: LLM 调用管理器实例
        """
        self._llm_manager = llm_manager
    
    async def analyze_group_profile(
        self,
        messages: List[str],
        current_profile: Dict
    ) -> Dict[str, List[str]]:
        """分析群聊画像
        
        从近期对话消息中提取群聊画像特征：
        - 群聊兴趣点
        - 氛围标签
        - 常用语/梗
        
        Args:
            messages: 近期对话消息列表
            current_profile: 当前画像数据（字典格式）
        
        Returns:
            分析结果字典：
            {
                "interests": ["技术交流", "游戏"],
                "atmosphere_tags": ["轻松", "技术范"],
                "common_expressions": ["yyds", "绝了"]
            }
        
        Examples:
            >>> messages = ["今天我们讨论了AI技术", "yyds!", "这个方案绝了"]
            >>> result = await analyzer.analyze_group_profile(messages, {})
            >>> print(result["interests"])
            ['AI技术']
        """
        prompt = self._build_group_analysis_prompt(messages, current_profile)
        
        try:
            response = await self._llm_manager.generate(
                prompt=prompt,
                module="profile_analysis"
            )
            
            # 解析 JSON 响应
            result = self._parse_json_response(response)
            logger.info("群聊画像分析完成")
            return result
        
        except Exception as e:
            logger.error(f"群聊画像分析失败: {e}")
            return {}
    
    async def analyze_user_profile(
        self,
        messages: List[str],
        current_profile: Dict
    ) -> Dict[str, str | List[str]]:
        """分析用户画像
        
        从用户近期对话中提取用户画像特征：
        - 当前情感状态
        - 性格标签
        - 兴趣爱好
        - 语言风格
        
        Args:
            messages: 用户近期对话列表
            current_profile: 当前画像数据（字典格式）
        
        Returns:
            分析结果字典：
            {
                "emotional_state": "愉快",
                "personality_tags": ["外向", "幽默"],
                "interests": ["编程", "游戏"],
                "language_style": "简洁"
            }
        
        Examples:
            >>> messages = ["哈哈哈今天天气真好", "最近在学Python"]
            >>> result = await analyzer.analyze_user_profile(messages, {})
            >>> print(result["emotional_state"])
            '愉快'
        """
        prompt = self._build_user_analysis_prompt(messages, current_profile)
        
        try:
            response = await self._llm_manager.generate(
                prompt=prompt,
                module="profile_analysis"
            )
            
            # 解析 JSON 响应
            result = self._parse_json_response(response)
            logger.info("用户画像分析完成")
            return result
        
        except Exception as e:
            logger.error(f"用户画像分析失败: {e}")
            return {}
    
    # ========================================================================
    # Prompt 构建
    # ========================================================================
    
    def _build_group_analysis_prompt(
        self, 
        messages: List[str], 
        current_profile: Dict
    ) -> str:
        """构建群聊画像分析 prompt
        
        Args:
            messages: 对话消息列表
            current_profile: 当前画像数据
        
        Returns:
            分析提示词
        """
        # 获取配置中的最大消息数
        config = get_config()
        max_messages = config.get("profile_max_messages_for_analysis") if hasattr(config, 'get') else 50
        
        # 限制消息数量
        limited_messages = messages[:max_messages]
        
        return f"""分析以下群聊对话，提取群聊画像特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

近期对话：
{chr(10).join(limited_messages)}

请分析并返回JSON格式结果：
{{
    "interests": ["群聊兴趣点1", "兴趣点2"],
    "atmosphere_tags": ["氛围标签1", "标签2"],
    "common_expressions": ["常用语或群内梗"]
}}

注意：
1. 基于对话内容客观分析
2. 兴趣点应是多次出现的话题
3. 氛围标签描述群聊整体风格
4. 常用语应为群内特有的表达

仅返回JSON，不要其他内容。"""
    
    def _build_user_analysis_prompt(
        self,
        messages: List[str],
        current_profile: Dict
    ) -> str:
        """构建用户画像分析 prompt
        
        Args:
            messages: 用户对话列表
            current_profile: 当前画像数据
        
        Returns:
            分析提示词
        """
        # 获取配置中的最大消息数
        config = get_config()
        max_messages = config.get("profile_max_messages_for_analysis") if hasattr(config, 'get') else 30
        
        # 限制消息数量
        limited_messages = messages[:max_messages]
        
        return f"""分析以下用户对话，提取用户画像特征。

当前画像：
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

用户近期对话：
{chr(10).join(limited_messages)}

请分析并返回JSON格式结果：
{{
    "emotional_state": "当前情感状态",
    "personality_tags": ["性格标签1", "标签2"],
    "interests": ["兴趣1", "兴趣2"],
    "language_style": "语言风格描述"
}}

注意：
1. 情感状态应为最近对话中流露的情绪
2. 性格标签基于对话风格推断
3. 兴趣应从对话内容中识别
4. 语言风格描述用户的表达习惯

仅返回JSON，不要其他内容。"""
    
    # ========================================================================
    # 辅助方法
    # ========================================================================
    
    def _parse_json_response(self, response: str) -> Dict:
        """解析 JSON 响应
        
        尝试从 LLM 响应中提取 JSON 内容。
        
        Args:
            response: LLM 响应文本
        
        Returns:
            解析后的字典，失败返回空字典
        """
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"无法解析JSON响应: {response[:100]}")
            return {}
