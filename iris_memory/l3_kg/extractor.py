"""实体和关系提取器"""

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import GraphNode, GraphEdge, ExtractionResult, NODE_TYPE_WHITELIST, RELATION_TYPE_WHITELIST
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
      "source_name": "源实体名称",
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
            node_name_to_id = {}
            
            for node_data in data.get("nodes", []):
                # 构建 properties，包含 active_users
                properties = node_data.get("properties", {})
                
                # 添加活跃用户信息（用于检索时基于用户ID扩展）
                active_users = context.get("active_users", [])
                if active_users:
                    properties["active_users"] = ",".join(active_users)
                
                node = GraphNode(
                    id="",  # 稍后生成
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
                node_name_to_id[node.name] = node.id
            
            # 构建边
            edges = []
            for edge_data in data.get("edges", []):
                source_id = node_name_to_id.get(edge_data["source_name"])
                target_id = node_name_to_id.get(edge_data["target_name"])
                
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
        """为活跃用户创建 Person 节点以及与提取实体的关系
        
        Args:
            active_users: 活跃用户 ID 列表
            existing_nodes: 已提取的节点列表
            context: 上下文信息
        
        Returns:
            (用户节点列表, 用户关系边列表)
        """
        user_nodes = []
        user_edges = []
        
        # 为每个活跃用户创建 Person 节点
        for user_id in active_users:
            user_node = GraphNode(
                id="",  # 稍后生成
                label="Person",
                name=user_id,
                content=f"用户 {user_id}",
                confidence=1.0,  # 用户ID置信度最高
                source_memory_id=context.get("source_memory_id"),
                group_id=context.get("group_id"),
                properties={"is_user": "true"}
            )
            user_node.id = user_node.generate_id()
            user_nodes.append(user_node)
        
        # 建立用户与提取实体的关系
        # 选择重要的实体类型进行关联
        important_labels = {"Topic", "Event", "Concept"}
        important_nodes = [n for n in existing_nodes if n.label in important_labels]
        
        for user_node in user_nodes:
            # 用户与每个重要实体建立 DISCUSSED 关系
            for entity_node in important_nodes[:5]:  # 最多关联5个实体
                edge = GraphEdge(
                    source_id=user_node.id,
                    target_id=entity_node.id,
                    relation_type="DISCUSSED",
                    confidence=0.8,
                    source_memory_id=context.get("source_memory_id")
                )
                user_edges.append(edge)
        
        # 用户之间的关系（KNOWS）
        if len(user_nodes) > 1:
            for i, user_node_1 in enumerate(user_nodes):
                for user_node_2 in user_nodes[i+1:]:
                    edge = GraphEdge(
                        source_id=user_node_1.id,
                        target_id=user_node_2.id,
                        relation_type="KNOWS",
                        confidence=0.7,
                        source_memory_id=context.get("source_memory_id")
                    )
                    user_edges.append(edge)
        
        if user_nodes:
            logger.info(
                f"为 {len(user_nodes)} 个活跃用户创建了 Person 节点，"
                f"关联 {len(user_edges)} 条边"
            )
        
        return user_nodes, user_edges
