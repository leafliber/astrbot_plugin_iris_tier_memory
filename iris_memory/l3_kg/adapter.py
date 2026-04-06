"""KuzuDB 图谱适配器"""

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .models import GraphNode, GraphEdge
import kuzu
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = get_logger("l3_kg")


def _build_map_literal(properties: dict) -> str:
    """构建 MAP 字面量字符串
    
    Args:
        properties: 属性字典
        
    Returns:
        MAP 字面量字符串，如 map(['key1', 'key2'], ['val1', 'val2'])
    """
    if not properties:
        return "map([], [])"
    
    keys = []
    values = []
    for k, v in properties.items():
        escaped_key = str(k).replace("\\", "\\\\").replace("'", "\\'")
        escaped_val = str(v).replace("\\", "\\\\").replace("'", "\\'")
        keys.append(f"'{escaped_key}'")
        values.append(f"'{escaped_val}'")
    
    return f"map([{', '.join(keys)}], [{', '.join(values)}])"


class L3KGAdapter(Component):
    """KuzuDB 图谱适配器
    
    使用 KuzuDB 嵌入式图数据库存储实体关系图谱。
    支持：
    - 动态节点类型（通过 label 字段）
    - 动态关系类型（通过 relation_type 字段）
    - MAP 类型存储扩展属性
    - 路径扩展检索
    """
    
    @property
    def name(self) -> str:
        return "l3_kg"
    
    async def initialize(self) -> None:
        """初始化 KuzuDB 数据库
        
        创建数据库连接和 schema。
        如果初始化失败，标记为不可用但不阻塞主流程。
        """
        config = get_config()
        
        if not config.get("l3_kg.enable"):
            logger.info("L3 知识图谱未启用")
            self._is_available = False
            return
        
        self._persist_dir = config.data_dir / "kuzu"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            db_path = self._persist_dir / "graph.kuzu"
            self._db = kuzu.Database(str(db_path))
            self._conn = kuzu.Connection(self._db)
            
            # 创建 schema
            await self._create_schema()
            
            self._is_available = True
            logger.info(f"KuzuDB 初始化成功：{self._persist_dir}")
        except Exception as e:
            logger.error(f"KuzuDB 初始化失败：{e}")
            self._is_available = False
    
    async def _create_schema(self):
        """创建图谱 schema
        
        使用 MAP 类型存储动态属性，使用 DOUBLE 存储浮点数。
        """
        self._conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS Entity (
                id STRING PRIMARY KEY,
                label STRING,
                name STRING,
                content STRING,
                confidence DOUBLE,
                access_count INT64,
                last_access_time TIMESTAMP,
                created_time TIMESTAMP,
                source_memory_id STRING,
                group_id STRING,
                properties MAP(STRING, STRING)
            )
        """)
        
        self._conn.execute("""
            CREATE REL TABLE IF NOT EXISTS Related (
                FROM Entity TO Entity,
                relation_type STRING,
                weight DOUBLE,
                confidence DOUBLE,
                access_count INT64,
                last_access_time TIMESTAMP,
                created_time TIMESTAMP,
                source_memory_id STRING,
                properties MAP(STRING, STRING)
            )
        """)
        
        logger.debug("KuzuDB schema 创建完成")
    
    async def add_node(self, node: GraphNode) -> bool:
        """添加节点
        
        Args:
            node: 图谱节点对象
            
        Returns:
            成功返回 True，失败返回 False
        """
        if not self._is_available:
            return False
        
        try:
            map_literal = _build_map_literal(node.properties)
            
            query = f"""
                MERGE (e:Entity {{id: $id}})
                SET e.label = $label,
                    e.name = $name,
                    e.content = $content,
                    e.confidence = $confidence,
                    e.access_count = $access_count,
                    e.last_access_time = $last_access_time,
                    e.created_time = $created_time,
                    e.source_memory_id = $source_memory_id,
                    e.group_id = $group_id,
                    e.properties = {map_literal}
            """
            self._conn.execute(query, {
                "id": node.id,
                "label": node.label,
                "name": node.name,
                "content": node.content,
                "confidence": node.confidence,
                "access_count": node.access_count,
                "last_access_time": node.last_access_time or datetime.now(),
                "created_time": node.created_time,
                "source_memory_id": node.source_memory_id,
                "group_id": node.group_id,
            })
            logger.debug(f"节点添加成功：{node.id}")
            return True
        except Exception as e:
            logger.error(f"添加节点失败：{e}")
            return False
    
    async def add_edge(self, edge: GraphEdge) -> bool:
        """添加关系边
        
        Args:
            edge: 图谱边对象
            
        Returns:
            成功返回 True，失败返回 False
        """
        if not self._is_available:
            return False
        
        try:
            map_literal = _build_map_literal(edge.properties)
            
            query = f"""
                MATCH (src:Entity {{id: $source_id}})
                MATCH (tgt:Entity {{id: $target_id}})
                MERGE (src)-[r:Related {{relation_type: $relation_type}}]->(tgt)
                SET r.weight = $weight,
                    r.confidence = $confidence,
                    r.access_count = $access_count,
                    r.last_access_time = $last_access_time,
                    r.created_time = $created_time,
                    r.source_memory_id = $source_memory_id,
                    r.properties = {map_literal}
            """
            self._conn.execute(query, {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "weight": edge.weight,
                "confidence": edge.confidence,
                "access_count": edge.access_count,
                "last_access_time": edge.last_access_time or datetime.now(),
                "created_time": edge.created_time,
                "source_memory_id": edge.source_memory_id,
            })
            logger.debug(f"边添加成功：{edge.generate_id()}")
            return True
        except Exception as e:
            logger.error(f"添加边失败：{e}")
            return False
    
    async def expand_from_nodes(
        self, 
        node_ids: list[str], 
        max_depth: int = 2,
        group_id: Optional[str] = None
    ) -> tuple[list[dict], list[dict]]:
        """路径扩展检索
        
        从指定节点出发，查找相关路径。
        
        Args:
            node_ids: 起始节点ID列表
            max_depth: 最大路径深度（跳跃次数）
            group_id: 群聊ID（用于隔离）
            
        Returns:
            (节点列表, 边列表)
        """
        if not self._is_available:
            return [], []
        
        try:
            # KuzuDB 变长路径语法：[:Related*min..max]
            query = """
                MATCH path = (start:Entity)-[:Related*1..%d]-(target:Entity)
                WHERE start.id IN $node_ids
                AND ($group_id IS NULL OR start.group_id = $group_id)
                RETURN 
                    nodes(path) as nodes,
                    relationships(path) as edges
            """ % max_depth
            
            result = self._conn.execute(query, {
                "node_ids": node_ids,
                "group_id": group_id
            })
            
            nodes = []
            edges = []
            for row in result:
                path_nodes = row[0] if row[0] else []
                path_edges = row[1] if row[1] else []
                for n in path_nodes:
                    if isinstance(n, dict) and "id" in n:
                        nodes.append(n)
                for e in path_edges:
                    if isinstance(e, dict):
                        edges.append(e)
            
            nodes = list({n["id"]: n for n in nodes}.values())
            edges = list({f"{e.get('source', '')}-{e.get('relation_type', '')}-{e.get('target', '')}": e for e in edges}.values())
            
            logger.info(f"路径扩展检索完成：{len(nodes)} 个节点，{len(edges)} 条边")
            return nodes, edges
        except Exception as e:
            logger.error(f"路径扩展检索失败：{e}")
            return [], []
    
    async def get_stats(self) -> dict:
        """获取图谱统计信息
        
        Returns:
            包含节点数、边数、持久化路径等信息的字典
        """
        if not self._is_available:
            return {"available": False, "node_count": 0, "edge_count": 0, "node_types": {}, "relation_types": {}}
        
        try:
            node_count = self._conn.execute("MATCH (e:Entity) RETURN COUNT(e) as count").get_next()[0]
            edge_count = self._conn.execute("MATCH ()-[r:Related]->() RETURN COUNT(r) as count").get_next()[0]
            
            node_types_result = self._conn.execute("MATCH (e:Entity) RETURN e.label as label, COUNT(e) as count")
            node_types = {}
            for row in node_types_result:
                if row[0]:
                    node_types[row[0]] = row[1]
            
            relation_types_result = self._conn.execute("MATCH ()-[r:Related]->() RETURN r.relation_type as type, COUNT(r) as count")
            relation_types = {}
            for row in relation_types_result:
                if row[0]:
                    relation_types[row[0]] = row[1]
            
            return {
                "available": True,
                "node_count": node_count,
                "edge_count": edge_count,
                "node_types": node_types,
                "relation_types": relation_types,
                "persist_dir": str(self._persist_dir)
            }
        except Exception as e:
            logger.error(f"获取图谱统计失败：{e}")
            return {"available": False, "node_count": 0, "edge_count": 0, "node_types": {}, "relation_types": {}}
    
    async def get_all_nodes(self, limit: int = 100) -> list[dict]:
        """获取节点（用于前端展示）
        
        Args:
            limit: 最大返回数量，默认 100
        
        Returns:
            节点字典列表
        """
        if not self._is_available:
            return []
        
        try:
            result = self._conn.execute(f"""
                MATCH (e:Entity)
                RETURN e.id, e.label, e.name, e.content, e.confidence,
                       e.access_count, e.last_access_time, e.created_time,
                       e.source_memory_id, e.group_id, e.properties
                LIMIT {limit}
            """)
            
            nodes = []
            for row in result:
                nodes.append({
                    "id": row[0],
                    "label": row[1],
                    "name": row[2],
                    "content": row[3],
                    "confidence": row[4],
                    "access_count": row[5],
                    "last_access_time": row[6],
                    "created_time": row[7],
                    "source_memory_id": row[8],
                    "group_id": row[9],
                    "properties": row[10]
                })
            
            logger.debug(f"获取到 {len(nodes)} 个节点")
            return nodes
            
        except Exception as e:
            logger.error(f"获取所有节点失败：{e}")
            return []
    
    async def get_random_person_node(self) -> Optional[dict]:
        if not self._is_available:
            return None
        
        try:
            import random
            result = self._conn.execute("""
                MATCH (e:Entity)
                WHERE e.label = 'Person'
                RETURN e.id, e.label, e.name, e.content, e.confidence
            """)
            
            nodes = []
            for row in result:
                nodes.append({
                    "id": row[0],
                    "label": row[1],
                    "name": row[2],
                    "content": row[3],
                    "confidence": row[4]
                })
            
            if nodes:
                return random.choice(nodes)
            
            return None
            
        except Exception as e:
            logger.error(f"获取随机Person节点失败：{e}")
            return None
    
    async def expand_from_node(
        self, 
        node_id: str, 
        depth: int = 2,
        max_nodes: int = 50,
        max_edges: int = 100
    ) -> tuple[list[dict], list[dict]]:
        if not self._is_available:
            return [], []
        
        depth = min(max(1, depth), 3)
        
        try:
            nodes_map = {}
            node_ids_to_query = [node_id]
            all_visited = {node_id}
            
            for current_depth in range(1, depth + 1):
                if len(nodes_map) >= max_nodes:
                    break
                
                remaining = max_nodes - len(nodes_map)
                
                if current_depth == 1:
                    query = f"""
                        MATCH (start:Entity {{id: $node_id}})-[r:Related]-(neighbor:Entity)
                        WHERE NOT neighbor.id IN $visited
                        RETURN DISTINCT neighbor.id, neighbor.label, neighbor.name, neighbor.content, neighbor.confidence
                        LIMIT {remaining}
                    """
                    result = self._conn.execute(query, {"node_id": node_id, "visited": list(all_visited)})
                else:
                    query = f"""
                        MATCH (start:Entity)-[r:Related]-(neighbor:Entity)
                        WHERE start.id IN $current_ids AND NOT neighbor.id IN $visited
                        RETURN DISTINCT neighbor.id, neighbor.label, neighbor.name, neighbor.content, neighbor.confidence
                        LIMIT {remaining}
                    """
                    result = self._conn.execute(query, {"current_ids": node_ids_to_query, "visited": list(all_visited)})
                
                node_ids_to_query = []
                for row in result:
                    nid = row[0]
                    if nid not in all_visited:
                        all_visited.add(nid)
                        node_ids_to_query.append(nid)
                        nodes_map[nid] = {
                            "id": nid,
                            "label": row[1],
                            "name": row[2],
                            "content": row[3],
                            "confidence": row[4]
                        }
                
                if not node_ids_to_query:
                    break
            
            start_node_result = self._conn.execute("""
                MATCH (e:Entity {id: $node_id})
                RETURN e.id, e.label, e.name, e.content, e.confidence
            """, {"node_id": node_id})
            
            for row in start_node_result:
                nodes_map[node_id] = {
                    "id": row[0],
                    "label": row[1],
                    "name": row[2],
                    "content": row[3],
                    "confidence": row[4]
                }
            
            edges_list = []
            seen_edges = set()
            
            if nodes_map:
                node_ids = list(nodes_map.keys())
                
                edges_result = self._conn.execute(f"""
                    MATCH (a:Entity)-[r:Related]->(b:Entity)
                    WHERE a.id IN $node_ids AND b.id IN $node_ids
                    RETURN a.id, b.id, r.relation_type, r.confidence
                    LIMIT {max_edges}
                """, {"node_ids": node_ids})
                
                for row in edges_result:
                    edge_key = f"{row[0]}->{row[1]}"
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges_list.append({
                            "source": row[0],
                            "target": row[1],
                            "relation": row[2],
                            "confidence": row[3]
                        })
            
            nodes_list = list(nodes_map.values())
            
            logger.debug(f"从节点 {node_id} 拓展深度 {depth}，获取 {len(nodes_list)} 节点，{len(edges_list)} 边")
            return nodes_list, edges_list
            
        except Exception as e:
            logger.error(f"从节点拓展失败：{e}")
            return [], []
    
    async def evict_nodes(self, node_ids: list[str]) -> int:
        """淘汰节点及关联边（用于定时任务）
        
        先删除关联边，再删除节点。
        
        Args:
            node_ids: 要淘汰的节点 ID 列表
        
        Returns:
            实际删除的节点数量
        """
        if not self._is_available or not node_ids:
            return 0
        
        try:
            # 1. 删除关联边
            self._conn.execute("""
                MATCH ()-[r:Related]-(e:Entity)
                WHERE e.id IN $node_ids
                DELETE r
            """, {"node_ids": node_ids})
            
            # 2. 删除节点
            self._conn.execute("""
                MATCH (e:Entity)
                WHERE e.id IN $node_ids
                DELETE e
            """, {"node_ids": node_ids})
            
            logger.info(f"已淘汰 {len(node_ids)} 个节点及其关联边")
            return len(node_ids)
            
        except Exception as e:
            logger.error(f"淘汰节点失败：{e}")
            return 0
    
    async def delete_by_group(self, group_id: str) -> int:
        """删除指定群聊的所有节点和边
        
        Args:
            group_id: 群聊ID
        
        Returns:
            删除的节点数量
        """
        if not self._is_available:
            return 0
        
        try:
            count_result = self._conn.execute("""
                MATCH (e:Entity)
                WHERE e.group_id = $group_id
                RETURN COUNT(e) as count
            """, {"group_id": group_id})
            
            node_count = count_result.get_next()[0]
            
            if node_count == 0:
                logger.debug(f"群聊 {group_id} 没有知识图谱节点")
                return 0
            
            self._conn.execute("""
                MATCH ()-[r:Related]-(e:Entity)
                WHERE e.group_id = $group_id
                DELETE r
            """, {"group_id": group_id})
            
            self._conn.execute("""
                MATCH (e:Entity)
                WHERE e.group_id = $group_id
                DELETE e
            """, {"group_id": group_id})
            
            logger.info(f"已删除群聊 {group_id} 的 {node_count} 个节点及其关联边")
            return node_count
            
        except Exception as e:
            logger.error(f"删除群聊知识图谱失败: {e}", exc_info=True)
            return 0
    
    async def delete_all(self) -> int:
        """删除所有节点和边
        
        Returns:
            删除的节点数量
        """
        if not self._is_available:
            return 0
        
        try:
            count_result = self._conn.execute("""
                MATCH (e:Entity)
                RETURN COUNT(e) as count
            """)
            
            node_count = count_result.get_next()[0]
            
            if node_count == 0:
                return 0
            
            self._conn.execute("""
                MATCH ()-[r:Related]->()
                DELETE r
            """)
            
            self._conn.execute("""
                MATCH (e:Entity)
                DELETE e
            """)
            
            logger.info(f"已删除所有知识图谱节点，共 {node_count} 个")
            return node_count
            
        except Exception as e:
            logger.error(f"删除所有知识图谱失败: {e}", exc_info=True)
            return 0
    
    async def delete_by_user(self, user_id: str, group_id: Optional[str] = None) -> int:
        """删除与指定用户相关的节点
        
        注意：由于知识图谱节点没有直接的 user_id 字段，
        此方法通过节点名称匹配用户ID来删除。
        这是一个近似实现，可能不精确。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID（可选）
        
        Returns:
            删除的节点数量
        """
        if not self._is_available:
            return 0
        
        try:
            if group_id:
                count_result = self._conn.execute("""
                    MATCH (e:Entity)
                    WHERE e.group_id = $group_id AND e.name = $user_id
                    RETURN COUNT(e) as count
                """, {"group_id": group_id, "user_id": user_id})
            else:
                count_result = self._conn.execute("""
                    MATCH (e:Entity)
                    WHERE e.name = $user_id
                    RETURN COUNT(e) as count
                """, {"user_id": user_id})
            
            node_count = count_result.get_next()[0]
            
            if node_count == 0:
                logger.debug(f"用户 {user_id} 没有知识图谱节点")
                return 0
            
            if group_id:
                self._conn.execute("""
                    MATCH ()-[r:Related]-(e:Entity)
                    WHERE e.group_id = $group_id AND e.name = $user_id
                    DELETE r
                """, {"group_id": group_id, "user_id": user_id})
                
                self._conn.execute("""
                    MATCH (e:Entity)
                    WHERE e.group_id = $group_id AND e.name = $user_id
                    DELETE e
                """, {"group_id": group_id, "user_id": user_id})
            else:
                self._conn.execute("""
                    MATCH ()-[r:Related]-(e:Entity)
                    WHERE e.name = $user_id
                    DELETE r
                """, {"user_id": user_id})
                
                self._conn.execute("""
                    MATCH (e:Entity)
                    WHERE e.name = $user_id
                    DELETE e
                """, {"user_id": user_id})
            
            logger.info(f"已删除用户 {user_id} 的 {node_count} 个知识图谱节点")
            return node_count
            
        except Exception as e:
            logger.error(f"删除用户知识图谱失败: {e}", exc_info=True)
            return 0
    
    async def shutdown(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
        if self._db:
            self._db.close()
        self._reset_state()
        logger.info("KuzuDB 已关闭")
