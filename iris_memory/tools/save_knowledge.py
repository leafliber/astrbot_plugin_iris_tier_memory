"""保存知识 LLM Tool"""

from astrbot.api import filter
from iris_memory.core import get_logger
from iris_memory.l3_kg import GraphNode, GraphEdge
from iris_memory.core.lifecycle import get_component_manager

logger = get_logger("tools")


@filter.llm_tool(name="save_knowledge")
async def save_knowledge(
    nodes: list[dict],
    edges: list[dict]
) -> str:
    """保存知识到图谱
    
    允许 LLM 手动添加实体和关系到知识图谱中。
    
    Args:
        nodes: 节点列表，每个节点包含：
            - label: 节点类型（如 "Person", "Event", "Concept"）
            - name: 实体名称
            - content: 实体描述
            - confidence: 置信度（可选，默认 1.0）
        edges: 边列表，每个边包含：
            - source_name: 源实体名称（必须在 nodes 中定义）
            - target_name: 目标实体名称（必须在 nodes 中定义）
            - relation_type: 关系类型（如 "KNOWS", "RELATED_TO"）
            - confidence: 置信度（可选，默认 1.0）
    
    Returns:
        操作结果描述
    
    Example:
        nodes = [
            {"label": "Person", "name": "Alice", "content": "Alice is a software engineer", "confidence": 0.9},
            {"label": "Event", "name": "Project X", "content": "A secret AI project", "confidence": 0.8}
        ]
        edges = [
            {"source_name": "Alice", "target_name": "Project X", "relation_type": "WORKED_ON", "confidence": 0.85}
        ]
    """
    try:
        # 获取图谱适配器
        component_manager = get_component_manager()
        kg_adapter = component_manager.get_component("l3_kg")
        
        if not kg_adapter or not kg_adapter._is_available:
            return "知识图谱不可用"
        
        if not nodes:
            return "未提供任何节点"
        
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
        return f"成功保存 {added_nodes} 个节点和 {added_edges} 条边到知识图谱"
    
    except Exception as e:
        logger.error(f"保存知识失败：{e}")
        return f"保存失败：{str(e)}"
