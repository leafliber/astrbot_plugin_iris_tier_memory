"""
Iris Tier Memory - 图增强检索器

利用 L3 知识图谱扩展 L2 记忆检索结果，发现更多关联信息。

增强策略：
1. 从查询文本提取关键词，在图谱中搜索匹配节点
2. 从 L2 记忆内容中提取实体名称，在图谱中搜索匹配节点
3. 对找到的节点进行路径扩展，发现关联实体和关系
"""

from typing import List, Optional, Tuple, Set, cast
from iris_memory.core import get_logger, ComponentManager
from iris_memory.config import get_config
from iris_memory.l2_memory.models import MemorySearchResult
from iris_memory.l3_kg.retriever import GraphRetriever
from iris_memory.l3_kg.adapter import L3KGAdapter
import re

logger = get_logger("enhancement.graph_enhancement")


class GraphEnhancer:
    """图增强检索器
    
    利用 L3 知识图谱扩展 L2 记忆检索结果。
    
    工作流程：
    1. 从查询文本和 L2 记忆内容中提取关键词/实体名
    2. 在图谱中搜索匹配的节点
    3. 对匹配节点进行路径扩展
    4. 返回图谱上下文文本
    
    Examples:
        >>> enhancer = GraphEnhancer(component_manager)
        >>> enhanced_results, graph_context = await enhancer.enhance(
        ...     memories=vector_results,
        ...     group_id="group_123",
        ...     query="用户喜欢什么"
        ... )
    """
    
    def __init__(self, component_manager: ComponentManager):
        """初始化图增强检索器
        
        Args:
            component_manager: 组件管理器实例
        """
        self._manager = component_manager
        self._l3_retriever: Optional[GraphRetriever] = None
        self._l3_adapter: Optional[L3KGAdapter] = None
        self._config = get_config()
    
    def _get_l3_retriever(self) -> Optional[GraphRetriever]:
        """获取 L3 图谱检索器
        
        Returns:
            GraphRetriever 实例，不可用时返回 None
        """
        if self._l3_retriever is None:
            adapter = self._get_l3_adapter()
            if adapter and adapter.is_available:
                self._l3_retriever = GraphRetriever(adapter)
        
        return self._l3_retriever
    
    def _get_l3_adapter(self) -> Optional[L3KGAdapter]:
        """获取 L3 图谱适配器
        
        Returns:
            L3KGAdapter 实例，不可用时返回 None
        """
        if self._l3_adapter is None:
            adapter = self._manager.get_component("l3_kg")
            if adapter and adapter.is_available:
                self._l3_adapter = cast(L3KGAdapter, adapter)
        
        return self._l3_adapter
    
    async def enhance(
        self,
        memories: List[MemorySearchResult],
        group_id: Optional[str] = None,
        query: Optional[str] = None,
        node_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[MemorySearchResult], str]:
        """对向量检索结果进行图增强
        
        从查询文本和 L2 记忆内容中提取关键词，在图谱中搜索匹配节点，
        同时支持外部传入节点 ID 和用户 ID，合并后进行路径扩展，返回图谱上下文文本。
        
        Args:
            memories: L2 向量检索结果
            group_id: 群聊 ID（用于图谱检索隔离）
            query: 原始查询文本
            node_ids: 外部传入的节点 ID（来自 L2 记忆 metadata）
            user_id: 当前用户 ID（用于基于用户相关的节点扩展）
        
        Returns:
            (原记忆列表, 图谱上下文文本)
        
        Examples:
            >>> enhancer = GraphEnhancer(component_manager)
            >>> enhanced, graph_text = await enhancer.enhance(
            ...     memories=vector_results,
            ...     group_id="group_123",
            ...     query="用户喜欢什么",
            ...     node_ids=["node_1", "node_2"],
            ...     user_id="user_456"
            ... )
        """
        if not memories:
            return [], ""
        
        # 检查是否启用图增强
        enable_graph = self._config.get("l2_memory.enable_graph_enhancement", False)
        if not enable_graph:
            logger.debug("图增强未启用，跳过")
            return memories, ""
        
        # 获取 L3 检索器
        retriever = self._get_l3_retriever()
        adapter = self._get_l3_adapter()
        if not retriever or not adapter:
            logger.debug("L3 图谱不可用，跳过图增强")
            return memories, ""
        
        try:
            # 1. 收集所有起始节点 ID
            all_node_ids: Set[str] = set()
            
            # 1.1 添加外部传入的节点 ID
            if node_ids:
                all_node_ids.update(node_ids)
                logger.debug(f"接收到 {len(node_ids)} 个外部节点 ID")
            
            # 1.2 基于用户 ID 搜索相关节点
            if user_id:
                user_node_ids = await self._search_nodes_by_user(
                    user_id=user_id,
                    adapter=adapter,
                    group_id=group_id
                )
                all_node_ids.update(user_node_ids)
                logger.debug(f"用户 {user_id} 相关节点：{len(user_node_ids)} 个")
            
            # 1.3 从查询和记忆内容中提取关键词，搜索匹配节点
            keywords = self._extract_keywords(query, memories)
            
            if keywords:
                keyword_node_ids = await self._search_nodes_by_keywords(
                    keywords=keywords,
                    adapter=adapter,
                    group_id=group_id
                )
                all_node_ids.update(keyword_node_ids)
                logger.debug(f"关键词搜索找到 {len(keyword_node_ids)} 个节点")
            
            if not all_node_ids:
                logger.debug("未找到任何起始节点，跳过图增强")
                return memories, ""
            
            logger.debug(f"图增强共收集 {len(all_node_ids)} 个起始节点")
            
            # 2. 执行图谱路径扩展
            nodes, edges = await retriever.retrieve_with_expansion(
                memory_node_ids=list(all_node_ids),
                group_id=group_id
            )
            
            if not nodes:
                logger.debug("图谱路径扩展未找到相关节点")
                return memories, ""
            
            # 3. 格式化图谱结果为上下文文本
            graph_context = retriever.format_for_context(nodes, edges)
            
            logger.info(
                f"图增强完成：提取 {len(keywords)} 个关键词，"
                f"外部节点 {len(node_ids) if node_ids else 0} 个，"
                f"用户节点 {len(user_node_ids) if user_id else 0} 个，"
                f"共 {len(all_node_ids)} 个起始节点，"
                f"扩展出 {len(nodes)} 个节点、{len(edges)} 条边"
            )
            
            # 4. 更新节点访问计数
            expanded_node_ids = [node.get("id") for node in nodes if node.get("id")]
            if expanded_node_ids:
                await retriever.update_access_count(expanded_node_ids)
            
            return memories, graph_context
        
        except Exception as e:
            logger.error(f"图增强失败：{e}", exc_info=True)
            return memories, ""
    
    def _extract_keywords(
        self,
        query: Optional[str],
        memories: List[MemorySearchResult]
    ) -> Set[str]:
        """从查询文本和记忆内容中提取关键词/实体名
        
        Args:
            query: 查询文本
            memories: L2 记忆检索结果
        
        Returns:
            关键词集合
        """
        keywords: Set[str] = set()
        
        # 1. 从查询中提取关键词
        if query:
            query_keywords = self._tokenize(query)
            keywords.update(query_keywords)
        
        # 2. 从记忆内容中提取实体名（通常是名词短语）
        for memory in memories[:5]:  # 只取前5条记忆
            content = memory.entry.content
            # 提取引号中的内容（通常是人名、地点等实体）
            quoted = re.findall(r'[""「」『』]([^""「」『』]+)[""「」『』]', content)
            keywords.update(quoted)
            
            # 提取可能的实体名（2-6个字的中文词组）
            entities = re.findall(r'[\u4e00-\u9fa5]{2,6}', content)
            # 过滤掉常见动词和虚词
            stopwords = {'什么', '怎么', '如何', '为什么', '这个', '那个', '今天', '昨天', '明天', '喜欢', '觉得', '想要', '可以', '知道', '一下', '一些'}
            entities = [e for e in entities if e not in stopwords and len(e) >= 2]
            keywords.update(entities)
        
        # 过滤太短的关键词
        keywords = {k for k in keywords if len(k) >= 2}
        
        logger.debug(f"提取到 {len(keywords)} 个关键词：{list(keywords)[:10]}...")
        return keywords
    
    def _tokenize(self, text: str) -> Set[str]:
        """简单的中文分词
        
        Args:
            text: 输入文本
        
        Returns:
            关键词集合
        """
        # 简单分词：提取中文词组
        keywords: Set[str] = set()
        
        # 提取中文词组（2-6个字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
        keywords.update(chinese_words)
        
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        keywords.update(english_words.lower() for english_words in english_words)
        
        return keywords
    
    async def _search_nodes_by_user(
        self,
        user_id: str,
        adapter: L3KGAdapter,
        group_id: Optional[str] = None
    ) -> Set[str]:
        """搜索与用户ID相关的图谱节点
        
        基于用户ID在图谱中搜索相关节点：
        1. **用户节点本身**：Person 节点，name = user_id（优先级最高）
        2. **用户相关实体**：properties.active_users 包含该用户ID
        3. **用户关联的邻居节点**：通过 DISCUSSED/KNOWS 关系连接的节点
        
        Args:
            user_id: 用户 ID
            adapter: L3 图谱适配器
            group_id: 群聊 ID
        
        Returns:
            匹配的节点 ID 集合
        """
        if not adapter._is_available or not user_id:
            return set()
        
        matched_ids: Set[str] = set()
        
        try:
            # 策略1：用户节点本身（Person 类型，name = user_id）
            # 这是最重要的节点，作为路径扩展的起点
            query1 = """
                MATCH (e:Entity)
                WHERE e.name = $user_id
                AND e.label = 'Person'
                AND ($group_id IS NULL OR e.group_id = $group_id)
                RETURN e.id, e.name, e.label
                LIMIT 1
            """
            
            result1 = adapter._conn.execute(query1, {
                "user_id": user_id,
                "group_id": group_id
            })
            
            for row in result1:
                node_id = row[0]
                if node_id:
                    matched_ids.add(node_id)
                    logger.debug(f"找到用户节点：{row[1]} ({row[2]})")
            
            # 策略2：用户直接关联的节点（1跳邻居）
            if matched_ids:
                user_node_id = list(matched_ids)[0]
                query2 = """
                    MATCH (u:Entity {id: $user_node_id})-[:Related]-(neighbor:Entity)
                    WHERE ($group_id IS NULL OR neighbor.group_id = $group_id)
                    RETURN DISTINCT neighbor.id, neighbor.name, neighbor.label
                    LIMIT 10
                """
                
                result2 = adapter._conn.execute(query2, {
                    "user_node_id": user_node_id,
                    "group_id": group_id
                })
                
                for row in result2:
                    neighbor_id = row[0]
                    if neighbor_id:
                        matched_ids.add(neighbor_id)
                        logger.debug(f"用户关联节点：{row[1]} ({row[2]})")
            
            # 策略3：properties.active_users 包含该用户ID（兼容旧数据）
            query3 = """
                MATCH (e:Entity)
                WHERE e.properties.active_users CONTAINS $user_id
                AND ($group_id IS NULL OR e.group_id = $group_id)
                RETURN e.id, e.name, e.label
                LIMIT 5
            """
            
            result3 = adapter._conn.execute(query3, {
                "user_id": user_id,
                "group_id": group_id
            })
            
            for row in result3:
                node_id = row[0]
                if node_id:
                    matched_ids.add(node_id)
            
            logger.debug(f"用户 {user_id} 相关图谱节点：{len(matched_ids)} 个")
            return matched_ids
        
        except Exception as e:
            logger.error(f"搜索用户相关节点失败：{e}")
            return set()
    
    async def _search_nodes_by_keywords(
        self,
        keywords: Set[str],
        adapter: L3KGAdapter,
        group_id: Optional[str] = None
    ) -> Set[str]:
        """在图谱中搜索匹配关键词的节点
        
        Args:
            keywords: 关键词集合
            adapter: L3 图谱适配器
            group_id: 群聊 ID
        
        Returns:
            匹配的节点 ID 集合
        """
        if not adapter._is_available or not keywords:
            return set()
        
        matched_ids: Set[str] = set()
        
        try:
            # 构建搜索查询：匹配 name 或 content 字段
            for keyword in keywords:
                # 搜索 name 字段（精确匹配或包含）
                query = """
                    MATCH (e:Entity)
                    WHERE (e.name CONTAINS $keyword OR e.content CONTAINS $keyword)
                    AND ($group_id IS NULL OR e.group_id = $group_id)
                    RETURN e.id, e.name, e.label
                    LIMIT 5
                """
                
                result = adapter._conn.execute(query, {
                    "keyword": keyword,
                    "group_id": group_id
                })
                
                for row in result:
                    node_id = row[0]
                    if node_id:
                        matched_ids.add(node_id)
            
            # 限制最大节点数
            if len(matched_ids) > 20:
                matched_ids = set(list(matched_ids)[:20])
            
            return matched_ids
        
        except Exception as e:
            logger.error(f"搜索图谱节点失败：{e}")
            return set()
