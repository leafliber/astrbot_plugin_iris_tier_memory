"""获取群聊画像 LLM Tool"""

from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from iris_memory.core import get_logger, get_component_manager
from iris_memory.profile import GroupProfileManager
from iris_memory.profile.models import GroupProfile

logger = get_logger("tools")


@dataclass
class GetGroupProfileTool(FunctionTool[AstrAgentContext]):
    """获取群聊画像的Tool
    
    提供群聊画像查询功能，LLM 可通过此 Tool 获取群聊的整体特征和行为模式。
    
    Attributes:
        name: Tool 名称
        description: Tool 描述
        parameters: Tool 参数定义
    
    Examples:
        Tool 会返回格式化的群聊画像信息：
        ```
        ## 群聊画像 - 技术交流群
        
        **当前话题**: AI技术进展
        **最近互动**: 2026-03-29 18:00:00
        
        **群聊兴趣**: 技术, 编程, AI
        **氛围标签**: 轻松, 技术范
        **核心特征**: 技术交流群
        
        **活跃用户**: user1, user2, user3
        **常用语/梗**: yyds, 绝了
        
        **禁忌话题**: 政治, 宗教
        ```
    """
    
    name: str = "get_group_profile"
    description: str = "获取群聊画像，包含群聊主题、兴趣点、氛围标签等信息"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "string",
                    "description": "群聊ID（可选，不传则自动获取当前群聊）"
                }
            }
        }
    )
    
    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs
    ) -> ToolExecResult:
        """执行获取群聊画像操作
        
        Args:
            context: AstrBot执行上下文
            **kwargs: Tool参数
                - group_id: 群聊ID（可选）
        
        Returns:
            ToolExecResult: 包含群聊画像信息的执行结果
        """
        try:
            # 获取参数
            group_id = kwargs.get("group_id", "")
            
            # 如果未传group_id，尝试从上下文获取
            if not group_id:
                event = context.context.event
                from iris_memory.platform import get_adapter
                adapter = get_adapter(event)
                group_id = adapter.get_group_id(event)
            
            if not group_id:
                return ToolExecResult(
                    result="无法获取群聊ID，请手动指定group_id参数。"
                )
            
            # 获取画像存储组件
            manager = get_component_manager()
            profile_storage = manager.get_component("profile")
            
            if not profile_storage or not profile_storage.is_available:
                return ToolExecResult(
                    result="画像系统未启用或不可用。"
                )
            
            # 获取群聊画像
            group_manager = GroupProfileManager(profile_storage)
            profile = await group_manager.get_or_create(group_id)
            
            # 格式化输出
            result = self._format_group_profile(profile)
            
            logger.info(f"获取群聊画像: {group_id}")
            return ToolExecResult(result=result)
        
        except Exception as e:
            logger.error(f"获取群聊画像失败: {e}", exc_info=True)
            return ToolExecResult(
                result=f"获取群聊画像失败: {str(e)}"
            )
    
    def _format_group_profile(self, profile: GroupProfile) -> str:
        """格式化群聊画像为文本
        
        Args:
            profile: 群聊画像对象
        
        Returns:
            格式化的画像文本
        """
        lines = [
            f"## 群聊画像 - {profile.group_name or profile.group_id}",
            f"",
            f"**当前话题**: {profile.current_topic or '无'}",
            f"**最近互动**: {profile.last_interaction_time or '未知'}",
            f"",
            f"**群聊兴趣**: {', '.join(profile.interests) or '暂无'}",
            f"**氛围标签**: {', '.join(profile.atmosphere_tags) or '暂无'}",
            f"**核心特征**: {', '.join(profile.long_term_tags) or '暂无'}",
            f"",
            f"**活跃用户**: {', '.join(profile.active_users[:10]) or '暂无'}",
            f"**常用语/梗**: {', '.join(profile.common_expressions) or '暂无'}",
            f"",
            f"**禁忌话题**: {', '.join(profile.blacklist_topics) or '无'}"
        ]
        
        return chr(10).join(lines)
