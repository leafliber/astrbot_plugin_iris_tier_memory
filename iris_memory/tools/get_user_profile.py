"""获取用户画像 LLM Tool"""

from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from iris_memory.core import get_logger, get_component_manager
from iris_memory.config import get_config
from iris_memory.profile import UserProfileManager
from iris_memory.profile.models import UserProfile

logger = get_logger("tools")


@dataclass
class GetUserProfileTool(FunctionTool[AstrAgentContext]):
    """获取用户画像的Tool
    
    提供用户画像查询功能，LLM 可通过此 Tool 获取用户的个人特征和行为模式。
    
    Attributes:
        name: Tool 名称
        description: Tool 描述
        parameters: Tool 参数定义
    
    Examples:
        Tool 会返回格式化的用户画像信息：
        ```
        ## 用户画像 - 小明
        
        **用户昵称**: 小明
        **最近互动**: 2026-03-29 18:00:00
        
        **当前情绪**: 愉快
        **用户性格**: 外向, 幽默, 理性
        **用户兴趣**: Python, 机器学习, 游戏
        
        **用户对你的称呼**: 小助手
        **历史曾用ID**: user123_old
        
        **⚠️ 用户禁忌话题**: 个人隐私
        ```
    """
    
    name: str = "get_user_profile"
    description: str = "获取用户画像，包含用户性格、兴趣、情感状态等信息"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户ID（可选，不传则自动获取当前用户）"
                }
            }
        }
    )
    
    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs
    ) -> ToolExecResult:
        """执行获取用户画像操作
        
        Args:
            context: AstrBot执行上下文
            **kwargs: Tool参数
                - user_id: 用户ID（可选）
        
        Returns:
            ToolExecResult: 包含用户画像信息的执行结果
        """
        try:
            # 获取参数
            user_id = kwargs.get("user_id", "")
            
            # 如果未传user_id，尝试从上下文获取
            if not user_id:
                event = context.context.event
                from iris_memory.platform import get_adapter
                adapter = get_adapter(event)
                user_id = adapter.get_user_id(event)
                group_id = adapter.get_group_id(event)
            else:
                # 如果指定了 user_id，group_id 默认为 "default"
                group_id = "default"
            
            if not user_id:
                return ToolExecResult(
                    result="无法获取用户ID，请手动指定user_id参数。"
                )
            
            # 获取画像存储组件
            manager = get_component_manager()
            profile_storage = manager.get_component("profile")
            
            if not profile_storage or not profile_storage.is_available:
                return ToolExecResult(
                    result="画像系统未启用或不可用。"
                )
            
            # 根据群聊隔离配置决定 group_id
            config = get_config()
            effective_group_id = group_id if config.get("isolation_config.enable_group_isolation") else "default"
            
            # 获取用户画像
            user_manager = UserProfileManager(profile_storage)
            profile = await user_manager.get_or_create(user_id, effective_group_id)
            
            # 格式化输出
            result = self._format_user_profile(profile)
            
            logger.info(f"获取用户画像: {user_id} (群聊: {effective_group_id})")
            return ToolExecResult(result=result)
        
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}", exc_info=True)
            return ToolExecResult(
                result=f"获取用户画像失败: {str(e)}"
            )
    
    def _format_user_profile(self, profile: UserProfile) -> str:
        """格式化用户画像为文本
        
        Args:
            profile: 用户画像对象
        
        Returns:
            格式化的画像文本
        """
        lines = [
            f"## 用户画像 - {profile.user_name or profile.user_id}",
            f"",
            f"**用户昵称**: {profile.user_name or '未知'}",
            f"**最近互动**: {profile.last_interaction_time or '未知'}",
            f""
        ]
        
        # 中期信息（如果存在）
        if profile.current_emotional_state:
            lines.append(f"**当前情绪**: {profile.current_emotional_state}")
        
        if profile.personality_tags:
            lines.append(f"**用户性格**: {', '.join(profile.personality_tags)}")
        
        if profile.interests:
            lines.append(f"**用户兴趣**: {', '.join(profile.interests)}")
        
        if profile.occupation:
            lines.append(f"**职业/身份**: {profile.occupation}")
        
        if profile.language_style:
            lines.append(f"**语言风格**: {profile.language_style}")
        
        lines.append(f"")
        
        # 长期信息（如果存在）
        if profile.bot_relationship:
            lines.append(f"**用户对你的称呼**: {profile.bot_relationship}")
        
        if profile.historical_names:
            lines.append(f"**历史曾用ID**: {', '.join(profile.historical_names)}")
        
        if profile.taboo_topics:
            lines.append(f"**⚠️ 用户禁忌话题**: {', '.join(profile.taboo_topics)}")
        
        if profile.important_dates:
            dates_str = ", ".join([f"{d['date']}({d['description']})" for d in profile.important_dates])
            lines.append(f"**重要日期**: {dates_str}")
        
        if profile.important_events:
            lines.append(f"**重要事件**: {', '.join(profile.important_events)}")
        
        return chr(10).join(lines)
