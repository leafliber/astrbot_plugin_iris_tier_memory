"""保存知识 LLM Tool"""

from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from iris_memory.core import get_logger, get_component_manager
from iris_memory.l3_kg import GraphNode, GraphEdge

logger = get_logger("tools")


@dataclass
class SaveKnowledgeTool(FunctionTool[AstrAgentContext]):
    """保存知识到图谱的Tool
    
    允许LLM手动添加实体和关系到知识图谱中。
    """
    
    name: str = "save_knowledge"
    description: str = "保存知识到知识图谱，添加实体节点和关系边"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "description": "节点列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "节点类型（如 Person, Event, Concept）"
                            },
                            "name": {
                                "type": "string",
                                "description": "实体名称"
                            },
                            "content": {
                                "type": "string",
                                "description": "实体描述"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "置信度（0.0-1.0）",
                                "default": 1.0
                            }
                        },
                        "required": ["label", "name", "content"]
                    }
                },
                "edges": {
                    "type": "array",
                    "description": "边列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_name": {
                                "type": "string",
                                "description": "源实体名称（必须在nodes中定义）"
                            },
                            "target_name": {
                                "type": "string",
                                "description": "目标实体名称（必须在nodes中定义）"
                            },
                            "relation_type": {
                                "type": "string",
                                "description": "关系类型（如 KNOWS, RELATED_TO）"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "置信度（0.0-1.0）",
                                "default": 1.0
                            }
                        },
                        "required": ["source_name", "target_name", "relation_type"]
                    }
                }
            },
            "required": ["nodes"]
        }
    )
    
    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs
    ) -> ToolExecResult:
        """执行保存知识操作
        
        Args:
            context: AstrBot执行上下文
            **kwargs: Tool参数
                - nodes: 节点列表
                - edges: 边列表
        
        Returns:
            ToolExecResult: 包含操作结果的执行结果
        """
        try:
            # 获取参数
            nodes = kwargs.get("nodes", [])
            edges = kwargs.get("edges", [])
            
            from iris_memory.utils import sanitize_input
            for node_data in nodes:
                if "content" in node_data:
                    node_data["content"] = sanitize_input(node_data["content"], source="tool:save_knowledge")
                if "name" in node_data:
                    node_data["name"] = sanitize_input(node_data["name"], source="tool:save_knowledge")
            for edge_data in edges:
                if "relation_type" in edge_data:
                    edge_data["relation_type"] = sanitize_input(edge_data["relation_type"], source="tool:save_knowledge")
            
            # 获取图谱适配器
            component_manager = get_component_manager()
            kg_adapter = component_manager.get_component("l3_kg")
            
            if not kg_adapter or not kg_adapter._is_available:
                return ToolExecResult(result="知识图谱不可用")
            
            if not nodes:
                return ToolExecResult(result="未提供任何节点")
            
            # 构建 GraphNode 对象
            graph_nodes = []
            for node_data in nodes:
                node = GraphNode(
                    id="",
                    label=node_data["label"],
                    name=node_data["name"],
                    content=node_data["content"],
                    confidence=node_data.get("confidence", 1.0)
                )
                node.id = node.generate_id()
                graph_nodes.append(node)
            
            # 构建 GraphEdge 对象
            node_name_to_id = {n.name: n.id for n in graph_nodes}
            graph_edges = []
            for edge_data in edges:
                source_id = node_name_to_id.get(edge_data["source_name"])
                target_id = node_name_to_id.get(edge_data["target_name"])
                
                if source_id and target_id:
                    edge = GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relation_type=edge_data["relation_type"],
                        confidence=edge_data.get("confidence", 1.0)
                    )
                    graph_edges.append(edge)
            
            # 存储到图谱
            added_nodes = 0
            added_edges = 0
            
            for node in graph_nodes:
                if await kg_adapter.add_node(node):
                    added_nodes += 1
            
            for edge in graph_edges:
                if await kg_adapter.add_edge(edge):
                    added_edges += 1
            
            logger.info(f"手动保存知识：{added_nodes} 个节点，{added_edges} 条边")
            return ToolExecResult(
                result=f"成功保存 {added_nodes} 个节点和 {added_edges} 条边到知识图谱"
            )
        
        except Exception as e:
            logger.error(f"保存知识失败：{e}")
            return ToolExecResult(result=f"保存失败：{str(e)}")
