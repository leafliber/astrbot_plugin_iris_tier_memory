"""L3 知识图谱数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib

# 节点类型白名单
NODE_TYPE_WHITELIST = {"Person", "Event", "Concept", "Location", "Item", "Topic"}

# 关系类型白名单
RELATION_TYPE_WHITELIST = {
    "KNOWS", "MENTIONED", "RELATED_TO",
    "PART_OF", "LOCATED_AT", "HAPPENED_AT",
    "DISCUSSED", "PARTICIPATED"  # 新增：用户与实体/事件的关系
}


@dataclass
class GraphNode:
    """图谱节点
    
    Attributes:
        id: 节点唯一ID（基于内容hash生成）
        label: 节点类型标签（动态，优先使用白名单类型）
        name: 实体名称
        content: 完整描述内容
        confidence: 置信度 [0.3, 1.0]
        access_count: 访问次数
        last_access_time: 最后访问时间
        created_time: 创建时间
        source_memory_id: 来源记忆ID
        group_id: 群聊ID（用于隔离）
        properties: 扩展属性（存储为 MAP<STRING, STRING>）
    """
    id: str
    label: str
    name: str
    content: str
    confidence: float = 1.0
    access_count: int = 0
    last_access_time: Optional[datetime] = None
    created_time: datetime = field(default_factory=datetime.now)
    source_memory_id: Optional[str] = None
    group_id: Optional[str] = None
    properties: dict[str, str] = field(default_factory=dict)
    
    def generate_id(self) -> str:
        """基于实体名称生成唯一ID
        
        使用 label、name 的组合进行 MD5 hash，
        同一 label+name 的实体始终生成相同 ID，确保去重合并。
        生成格式：{label_lower}_{hash_prefix}
        
        Returns:
            节点唯一ID
        """
        content_hash = hashlib.md5(
            f"{self.label}:{self.name}".encode()
        ).hexdigest()
        return f"{self.label.lower()}_{content_hash[:12]}"
    
    def to_dict(self) -> dict:
        """转换为字典格式（用于 KuzuDB 存储）
        
        Returns:
            包含所有字段的字典
        """
        return {
            "id": self.id,
            "label": self.label,
            "name": self.name,
            "content": self.content,
            "confidence": self.confidence,
            "access_count": self.access_count,
            "last_access_time": self.last_access_time,
            "created_time": self.created_time,
            "source_memory_id": self.source_memory_id,
            "group_id": self.group_id,
            "properties": self.properties
        }


@dataclass
class GraphEdge:
    """图谱边
    
    Attributes:
        source_id: 源节点ID
        target_id: 目标节点ID
        relation_type: 关系类型（动态，优先使用白名单类型）
        weight: 边权重 [0.0, 1.0]
        confidence: 置信度
        access_count: 访问次数
        last_access_time: 最后访问时间
        created_time: 创建时间
        source_memory_id: 来源记忆ID
        properties: 扩展属性（存储为 MAP<STRING, STRING>）
    """
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    confidence: float = 1.0
    access_count: int = 0
    last_access_time: Optional[datetime] = None
    created_time: datetime = field(default_factory=datetime.now)
    source_memory_id: Optional[str] = None
    properties: dict[str, str] = field(default_factory=dict)
    
    def generate_id(self) -> str:
        """生成边唯一标识
        
        格式：{source_id}_{relation_type}_{target_id}
        
        Returns:
            边唯一标识
        """
        return f"{self.source_id}_{self.relation_type}_{self.target_id}"
    
    def to_dict(self) -> dict:
        """转换为字典格式（用于 KuzuDB 存储）
        
        Returns:
            包含所有字段的字典
        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "confidence": self.confidence,
            "access_count": self.access_count,
            "last_access_time": self.last_access_time,
            "created_time": self.created_time,
            "source_memory_id": self.source_memory_id,
            "properties": self.properties
        }


@dataclass
class ExtractionResult:
    """实体提取结果
    
    Attributes:
        nodes: 提取的节点列表
        edges: 提取的边列表
        extraction_confidence: 提取置信度
    """
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    extraction_confidence: float = 1.0
    
    def is_empty(self) -> bool:
        """检查结果是否为空
        
        Returns:
            如果没有节点和边则返回 True
        """
        return len(self.nodes) == 0 and len(self.edges) == 0
    
    def to_dict(self) -> dict:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "extraction_confidence": self.extraction_confidence
        }
