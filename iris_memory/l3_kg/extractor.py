"""实体和关系提取器"""

from typing import List
from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import GraphNode, GraphEdge, ExtractionResult, NODE_TYPE_WHITELIST, RELATION_TYPE_WHITELIST
from iris_memory.l2_memory import MemoryEntry
import json

logger = get_logger("l3_kg")


class EntityExtractor:
    """实体和关系提取器
    
    使用 LLM 从总结文本中提取实体（节点）和关系（边）。
    支持：
    - 动态节点类型（优先使用白名单）
    - 动态关系类型（优先使用白名单）
    - 置信度评估
    """
    
    def __init__(self, llm_manager):
        """初始化提取器
        
        Args:
            llm_manager: LLM 调用管理器
        """
        self.llm_manager = llm_manager
        self.config = get_config()
    
    async def extract_from_text(
        self, 
        text: str, 
        context: dict = None
    ) -> ExtractionResult:
        """从文本中提取实体和关系
        
        Args:
            text: 待提取的文本（总结内容）
            context: 上下文信息（group_id, source_memory_id 等）
        
        Returns:
            ExtractionResult: 提取结果，包含节点和边
        """
        if context is None:
            context = {}
        
        # 构建提取 prompt
        prompt = self._build_extraction_prompt(text)
        
        try:
            # 调用 LLM 提取
            response = await self.llm_manager.generate(
                prompt=prompt,
                module="l3_kg_extraction"
            )
            
            # 解析提取结果
            result = self._parse_extraction_result(response, context)
            
            logger.info(
                f"实体提取完成：{len(result.nodes)} 个节点，"
                f"{len(result.edges)} 条边"
            )
            
            return result
        except Exception as e:
            logger.error(f"实体提取失败：{e}")
            return ExtractionResult()
    
    async def extract_from_memories(
        self,
        memories: List[MemoryEntry],
        context: dict = None
    ) -> ExtractionResult:
        """从多条记忆中提取实体和关系
        
        将多条记忆合并后提取，用于 L3 知识图谱定时提取任务。
        
        Args:
            memories: 记忆条目列表
            context: 上下文信息
        
        Returns:
            ExtractionResult: 提取结果，包含节点和边
        """
        if not memories:
            return ExtractionResult()
        
        if context is None:
            context = {}
        
        combined_text = self._combine_memories(memories)
        
        if context.get("source_memory_id") is None and memories:
            context["source_memory_id"] = memories[0].id
        
        if context.get("group_id") is None and memories:
            context["group_id"] = memories[0].group_id
        
        active_users = set()
        for mem in memories:
            user_id = mem.metadata.get("user_id")
            if user_id:
                active_users.add(user_id)
        if active_users and not context.get("active_users"):
            context["active_users"] = list(active_users)
        
        logger.info(f"从 {len(memories)} 条记忆中提取实体和关系")
        
        return await self.extract_from_text(combined_text, context)
    
    def _combine_memories(self, memories: List[MemoryEntry]) -> str:
        """合并多条记忆内容
        
        Args:
            memories: 记忆条目列表
        
        Returns:
            合并后的文本
        """
        lines = []
        for i, mem in enumerate(memories, 1):
            user_info = ""
            user_id = mem.metadata.get("user_id")
            if user_id:
                user_info = f"[用户:{user_id}] "
            
            group_info = ""
            if mem.group_id:
                group_info = f"[群:{mem.group_id}] "
            
            lines.append(f"{i}. {user_info}{group_info}{mem.content}")
        
        return "\n".join(lines)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """构建提取 prompt
        
        Args:
            text: 待提取的文本
            
        Returns:
            构建好的 prompt
        """
        enable_whitelist = self.config.get("l3_kg.enable_type_whitelist", True)
        
        if enable_whitelist:
            whitelist_hint = f"""
## 节点类型白名单（优先使用）
{', '.join(NODE_TYPE_WHITELIST)}

## 关系类型白名单（优先使用）
{', '.join(RELATION_TYPE_WHITELIST)}
"""
        else:
            whitelist_hint = ""
        
        return f"""从以下文本中提取实体和关系。
{whitelist_hint}
## 提取规则
1. 识别文本中的关键实体（人物、事件、概念、地点、物品、话题）
2. 识别实体之间的关系
3. 如果实体类型不在白名单中，可以创建新类型，但要保持命名规范（PascalCase）
4. 如果关系类型不在白名单中，可以创建新类型（UPPER_CASE）
5. 评估提取置信度（0.3-1.0）

## 输出格式（JSON）
{{
  "nodes": [
    {{
      "label": "Person",
      "name": "实体名称",
      "content": "实体描述",
      "confidence": 0.9
    }}
  ],
  "edges": [
    {{
      "source_label": "Person",
      "source_name": "源实体名称",
      "target_label": "Event",
      "target_name": "目标实体名称",
      "relation_type": "KNOWS",
      "confidence": 0.8
    }}
  ],
  "extraction_confidence": 0.85
}}

## 待提取文本
{text}

## 输出
请严格按照 JSON 格式输出，不要添加任何其他内容。"""
    
    def _parse_extraction_result(
        self, 
        response: str, 
        context: dict
    ) -> ExtractionResult:
        """解析 LLM 提取结果
        
        Args:
            response: LLM 返回的 JSON 字符串
            context: 上下文信息
            
        Returns:
            解析后的 ExtractionResult 对象
        """
        try:
            # 清理响应（去除 markdown 代码块标记）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            data = json.loads(response.strip())
            
            # 构建节点
            nodes = []
            node_key_to_id = {}
            
            for node_data in data.get("nodes", []):
                properties = node_data.get("properties", {})
                
                active_users = context.get("active_users", [])
                if active_users:
                    properties["active_users"] = ",".join(active_users)
                
                node = GraphNode(
                    id="",
                    label=node_data["label"],
                    name=node_data["name"],
                    content=node_data["content"],
                    confidence=node_data.get("confidence", 1.0),
                    source_memory_id=context.get("source_memory_id"),
                    group_id=context.get("group_id"),
                    properties=properties
                )
                node.id = node.generate_id()
                nodes.append(node)
                node_key_to_id[f"{node.label}:{node.name}"] = node.id
            
            edges = []
            for edge_data in data.get("edges", []):
                source_label = edge_data.get("source_label")
                source_name = edge_data.get("source_name")
                target_label = edge_data.get("target_label")
                target_name = edge_data.get("target_name")
                
                source_id = None
                target_id = None
                
                if source_label and source_name:
                    source_id = node_key_to_id.get(f"{source_label}:{source_name}")
                if not source_id and source_name:
                    for key, nid in node_key_to_id.items():
                        if key.endswith(f":{source_name}"):
                            source_id = nid
                            break
                
                if target_label and target_name:
                    target_id = node_key_to_id.get(f"{target_label}:{target_name}")
                if not target_id and target_name:
                    for key, nid in node_key_to_id.items():
                        if key.endswith(f":{target_name}"):
                            target_id = nid
                            break
                
                if source_id and target_id:
                    edge = GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relation_type=edge_data["relation_type"],
                        confidence=edge_data.get("confidence", 1.0),
                        source_memory_id=context.get("source_memory_id")
                    )
                    edges.append(edge)
            
            # 添加用户节点和关系
            active_users = context.get("active_users", [])
            if active_users:
                user_nodes, user_edges = self._create_user_nodes_and_edges(
                    active_users=active_users,
                    existing_nodes=nodes,
                    context=context
                )
                nodes.extend(user_nodes)
                edges.extend(user_edges)
            
            return ExtractionResult(
                nodes=nodes,
                edges=edges,
                extraction_confidence=data.get("extraction_confidence", 1.0)
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败：{e}")
            logger.debug(f"原始响应：{response}")
            return ExtractionResult()
        except Exception as e:
            logger.error(f"解析提取结果失败：{e}")
            return ExtractionResult()
    
    def _create_user_nodes_and_edges(
        self,
        active_users: list[str],
        existing_nodes: list[GraphNode],
        context: dict
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """为活跃用户创建 Person 节点
        
        仅创建用户节点，不创建 DISCUSSED/KNOWS 边，
        避免产生大量低价值边导致图谱膨胀。
        
        Args:
            active_users: 活跃用户 ID 列表
            existing_nodes: 已提取的节点列表
            context: 上下文信息
        
        Returns:
            (用户节点列表, 空边列表)
        """
        user_nodes = []
        
        for user_id in active_users:
            user_node = GraphNode(
                id="",
                label="Person",
                name=user_id,
                content=f"用户 {user_id}",
                confidence=1.0,
                source_memory_id=context.get("source_memory_id"),
                group_id=context.get("group_id"),
                properties={"is_user": "true"}
            )
            user_node.id = user_node.generate_id()
            user_nodes.append(user_node)
        
        if user_nodes:
            logger.info(
                f"为 {len(user_nodes)} 个活跃用户创建了 Person 节点"
            )
        
        return user_nodes, []
