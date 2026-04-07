"""图谱检索器"""

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .adapter import L3KGAdapter
from datetime import datetime
import asyncio

logger = get_logger("l3_kg")


class GraphRetriever:
    """图谱检索器
    
    提供：
    - 路径扩展检索
    - 超时保护
    - 访问计数更新
    - 结果格式化
    """
    
    def __init__(self, adapter: L3KGAdapter):
        """初始化检索器
        
        Args:
            adapter: L3KGAdapter 实例
        """
        self.adapter = adapter
        self.config = get_config()
    
    async def retrieve_with_expansion(
        self,
        memory_node_ids: list[str],
        group_id: str = None
    ) -> tuple[list[dict], list[dict]]:
        """图增强检索：基于向量检索命中的记忆节点进行路径扩展
        
        Args:
            memory_node_ids: 向量检索命中的记忆对应的节点ID列表
            group_id: 群聊ID
        
        Returns:
            (节点列表, 边列表)
        """
        if not self.adapter._is_available:
            return [], []
        
        try:
            # 获取扩展深度配置
            max_depth = self.config.get("l3_kg.expansion_depth", 2)
            timeout_ms = self.config.get("l3_kg.timeout_ms", 1500)
            
            # 设置超时保护
            nodes, edges = await asyncio.wait_for(
                self.adapter.expand_from_nodes(
                    node_ids=memory_node_ids,
                    max_depth=max_depth,
                    group_id=group_id
                ),
                timeout=timeout_ms / 1000
            )
            
            logger.info(
                f"图增强检索完成：{len(nodes)} 个节点，"
                f"{len(edges)} 条边，深度 {max_depth}"
            )
            
            return nodes, edges
        except asyncio.TimeoutError:
            logger.warning(f"图增强检索超时（{timeout_ms}ms），跳过")
            return [], []
        except Exception as e:
            logger.error(f"图增强检索失败：{e}")
            return [], []
    
    async def update_access_count(self, node_ids: list[str]):
        """更新节点访问计数
        
        Args:
            node_ids: 需要更新的节点ID列表
        """
        if not self.adapter._is_available:
            return
        
        try:
            # 批量更新节点访问计数
            for node_id in node_ids:
                self.adapter._conn.execute("""
                    MATCH (e:Entity {id: $id})
                    SET e.access_count = e.access_count + 1,
                        e.last_access_time = $now
                """, {"id": node_id, "now": datetime.now()})
            
            logger.debug(f"更新了 {len(node_ids)} 个节点的访问计数")
        except Exception as e:
            logger.error(f"更新节点访问计数失败：{e}")
    
    def format_for_context(
        self,
        nodes: list[dict],
        edges: list[dict]
    ) -> str:
        """格式化图谱结果为上下文文本
        
        Args:
            nodes: 节点列表
            edges: 边列表
        
        Returns:
            格式化的文本，如果为空则返回空字符串
        """
        if not nodes:
            return ""
        
        lines = ["【知识图谱】"]
        
        node_lines = []
        for node in nodes:
            name = node.get("name", "")
            content = node.get("content", "")
            if name and content:
                node_lines.append(f"{name}:{content}")
            elif name:
                node_lines.append(name)
        
        if node_lines:
            lines.append("实体: " + " | ".join(node_lines[:10]))
        
        if edges:
            edge_lines = []
            for edge in edges[:10]:
                source = edge.get("source_name", "")
                target = edge.get("target_name", "")
                relation = edge.get("relation_type", "")
                if source and target:
                    edge_lines.append(f"{source}-{relation}->{target}")
            if edge_lines:
                lines.append("关系: " + " | ".join(edge_lines))
        
        return "\n".join(lines)
