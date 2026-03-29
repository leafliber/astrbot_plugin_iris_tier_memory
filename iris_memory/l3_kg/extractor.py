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
                node = GraphNode(
                    id="",  # 稍后生成
                    label=node_data["label"],
                    name=node_data["name"],
                    content=node_data["content"],
                    confidence=node_data.get("confidence", 1.0),
                    source_memory_id=context.get("source_memory_id"),
                    group_id=context.get("group_id")
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
