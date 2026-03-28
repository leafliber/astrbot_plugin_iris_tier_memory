"""图谱容量管理"""

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .adapter import L3KGAdapter
from datetime import datetime, timedelta

logger = get_logger("l3_kg")


class KGEvictionManager:
    """图谱容量管理器
    
    负责：
    - 计算遗忘评分
    - 淘汰过期实体和边
    - 维护图谱容量在限制内
    """
    
    def __init__(self, adapter: L3KGAdapter):
        """初始化容量管理器
        
        Args:
            adapter: L3KGAdapter 实例
        """
        self.adapter = adapter
        self.config = get_config()
    
    def calculate_forgetting_score(
        self,
        access_count: int,
        last_access_time: datetime,
        created_time: datetime,
        confidence: float
    ) -> float:
        """计算遗忘评分
        
        使用遗忘曲线计算：
        score = e^(-lambda * age) * (1 + log(access_count + 1)) * confidence
        
        Args:
            access_count: 访问次数
            last_access_time: 最后访问时间
            created_time: 创建时间
            confidence: 置信度
            
        Returns:
            遗忘评分 [0.0, 1.0]，越高越不容易被遗忘
        """
        try:
            # 获取遗忘参数
            lambda_decay = self.config.get("forgetting_lambda_kg", 0.01)
            retention_days = self.config.get("kg_retention_days", 30)
            
            # 计算时间因素（使用最后访问时间）
            now = datetime.now()
            time_since_access = (now - last_access_time).total_seconds() / 86400  # 转换为天数
            
            # 遗忘曲线：e^(-lambda * age)
            time_factor = max(0.0, min(1.0, 2.0 ** (-time_since_access / retention_days)))
            
            # 访问次数因素：log(access_count + 1)，归一化
            access_factor = min(1.0, (1.0 + (access_count / 10.0)) / 2.0)
            
            # 综合评分
            score = time_factor * access_factor * confidence
            
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"计算遗忘评分失败：{e}")
            return 0.5
    
    async def evict_expired_entities(self) -> tuple[int, int]:
        """淘汰过期实体和边
        
        根据 max_nodes 和 max_edges 限制，
        淘汰评分最低的实体和关联的边。
        
        Returns:
            (淘汰的节点数, 淘汰的边数)
        """
        if not self.adapter._is_available:
            return 0, 0
        
        try:
            max_nodes = self.config.get("l3_kg.max_nodes", 50000)
            max_edges = self.config.get("l3_kg.max_edges", 100000)
            threshold = self.config.get("forgetting_threshold_kg", 0.2)
            
            # 获取当前统计
            stats = await self.adapter.get_stats()
            current_nodes = stats.get("node_count", 0)
            current_edges = stats.get("edge_count", 0)
            
            evicted_nodes = 0
            evicted_edges = 0
            
            # 淘汰节点（如果超过限制）
            if current_nodes > max_nodes:
                # 查询评分最低的节点
                nodes_to_evict = current_nodes - max_nodes
                
                result = self.adapter._conn.execute("""
                    MATCH (e:Entity)
                    RETURN e.id as id, e.access_count as access_count,
                           e.last_access_time as last_access_time,
                           e.created_time as created_time,
                           e.confidence as confidence
                    ORDER BY e.access_count ASC, e.last_access_time ASC
                    LIMIT $limit
                """, {"limit": nodes_to_evict})
                
                node_ids_to_remove = []
                for row in result:
                    # 计算遗忘评分
                    score = self.calculate_forgetting_score(
                        access_count=row["access_count"],
                        last_access_time=row["last_access_time"],
                        created_time=row["created_time"],
                        confidence=row["confidence"]
                    )
                    
                    # 只淘汰低评分节点
                    if score < threshold:
                        node_ids_to_remove.append(row["id"])
                
                # 删除节点和关联的边
                for node_id in node_ids_to_remove:
                    # 先删除关联的边
                    self.adapter._conn.execute("""
                        MATCH (e:Entity {id: $id})-[r]-()
                        DELETE r
                    """, {"id": node_id})
                    
                    # 再删除节点
                    self.adapter._conn.execute("""
                        MATCH (e:Entity {id: $id})
                        DELETE e
                    """, {"id": node_id})
                    
                    evicted_nodes += 1
                
                evicted_edges = len(node_ids_to_remove) * 2  # 估算
            
            # 淘汰边（如果超过限制）
            if current_edges > max_edges:
                edges_to_evict = current_edges - max_edges
                
                # 删除权重最低的边
                self.adapter._conn.execute("""
                    MATCH ()-[r:Related]->()
                    WITH r ORDER BY r.weight ASC, r.access_count ASC
                    LIMIT $limit
                    DELETE r
                """, {"limit": edges_to_evict})
                
                evicted_edges += edges_to_evict
            
            if evicted_nodes > 0 or evicted_edges > 0:
                logger.info(
                    f"图谱淘汰完成：{evicted_nodes} 个节点，"
                    f"{evicted_edges} 条边"
                )
            
            return evicted_nodes, evicted_edges
        except Exception as e:
            logger.error(f"淘汰过期实体失败：{e}")
            return 0, 0
