"""读取记忆 LLM Tool"""

from typing import List
from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from iris_memory.core import get_logger
from iris_memory.l2_memory import MemorySearchResult
from iris_memory.core.lifecycle import get_component_manager

logger = get_logger("tools")


@dataclass
class ReadMemoryTool(FunctionTool[AstrAgentContext]):
    """从L2记忆库检索记忆的Tool
    
    允许LLM主动检索相关记忆。
    """
    
    name: str = "read_memory"
    description: str = "从长期记忆库检索相关记忆，用于回忆用户偏好、历史事件、关键信息等"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询文本（描述你想查找的记忆）"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的记忆数量（默认5条，最多10条）",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    )
    
    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs
    ) -> ToolExecResult:
        """执行读取记忆操作
        
        Args:
            context: AstrBot执行上下文
            **kwargs: Tool参数
                - query: 查询文本
                - top_k: 返回数量（可选）
        
        Returns:
            ToolExecResult: 包含检索结果的执行结果
        """
        try:
            # 获取参数
            query = kwargs.get("query", "").strip()
            top_k = min(kwargs.get("top_k", 5), 10)  # 最多10条
            
            if not query:
                return ToolExecResult(result="查询内容不能为空")
            
            # 获取event对象
            event = context.context.event
            
            # 使用Platform适配器获取上下文
            from iris_memory.platform import get_adapter
            adapter = get_adapter(event)
            user_id = adapter.get_user_id(event)
            group_id = adapter.get_group_id(event)
            
            # 处理隔离策略
            from iris_memory.config import get_config
            config = get_config()
            if not config.get("isolation_config.enable_group_memory_isolation"):
                group_id = None
            
            # 获取L2记忆适配器
            manager = get_component_manager()
            l2_adapter = manager.get_component("l2_memory")
            
            if not l2_adapter or not l2_adapter._is_available:
                return ToolExecResult(result="L2记忆库当前不可用")
            
            # 检索记忆
            results: List[MemorySearchResult] = await l2_adapter.search(
                query=query,
                top_k=top_k,
                group_id=group_id
            )
            
            if not results:
                return ToolExecResult(
                    result=f"未找到与「{query}」相关的记忆"
                )
            
            # 格式化输出
            output_lines = [f"找到 {len(results)} 条相关记忆：\n"]
            
            for idx, result in enumerate(results, 1):
                entry = result.entry
                output_lines.append(
                    f"{idx}. [{entry.id}] {entry.content}\n"
                    f"   相似度: {result.score:.2f} | 置信度: {entry.confidence:.2f}\n"
                    f"   时间: {entry.timestamp or '未知'}\n"
                )
            
            logger.info(
                f"LLM检索记忆: user={user_id}, group={group_id}, "
                f"query={query[:30]}..., results={len(results)}"
            )
            
            return ToolExecResult(result="\n".join(output_lines))
        
        except Exception as e:
            logger.error(f"检索记忆失败：{e}", exc_info=True)
            return ToolExecResult(result=f"检索记忆失败：{str(e)}")
