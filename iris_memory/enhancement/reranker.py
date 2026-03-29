"""
Iris Tier Memory - 记忆重排序器

使用 LLM 对检索结果进行重排序，提升相关性。
"""

from typing import List, Optional, TYPE_CHECKING
import re
from iris_memory.core import get_logger
from iris_memory.config import get_config
from iris_memory.l2_memory.models import MemorySearchResult

if TYPE_CHECKING:
    from iris_memory.llm.manager import LLMManager

logger = get_logger("enhancement.reranker")


class MemoryReranker:
    """记忆重排序器
    
    使用 LLM 对检索结果进行重排序。
    
    Features:
        - LLM 相关性打分
        - 轻量模型支持
        - 可配置开关
    
    Examples:
        >>> reranker = MemoryReranker(llm_manager)
        >>> reranked = await reranker.rerank(memories, query="用户喜欢什么")
    """
    
    def __init__(self, llm_manager: "LLMManager"):
        """初始化重排序器
        
        Args:
            llm_manager: LLM 调用管理器实例
        """
        self._llm_manager = llm_manager
        self._config = get_config()
    
    async def rerank(
        self,
        memories: List[MemorySearchResult],
        query: str,
        top_k: Optional[int] = None
    ) -> List[MemorySearchResult]:
        """对记忆列表进行重排序
        
        使用 LLM 为每条记忆打分，并根据分数重新排序。
        
        Args:
            memories: 记忆检索结果列表
            query: 原始查询文本
            top_k: 返回前 K 条结果（可选）
        
        Returns:
            重排序后的记忆列表
        
        Examples:
            >>> reranked = await reranker.rerank(
            ...     memories=results,
            ...     query="用户喜欢什么",
            ...     top_k=5
            ... )
        """
        if not memories:
            return []
        
        # 检查是否启用重排序
        enable_rerank = self._config.get("enhancement.enable_rerank", False)
        if not enable_rerank:
            logger.debug("重排序未启用，跳过")
            return memories
        
        # 检查 LLM Manager 是否可用
        if not self._llm_manager or not self._llm_manager.is_available:
            logger.warning("LLM Manager 不可用，跳过重排序")
            return memories
        
        # 构建重排序 Prompt
        prompt = self._build_rerank_prompt(memories, query)
        
        try:
            # 调用 LLM
            response = await self._llm_manager.generate(
                prompt=prompt,
                module="enhancement_rerank"
            )
            
            # 解析评分结果
            scores = self._parse_scores(response, len(memories))
            
            # 根据分数重新排序
            reranked = sorted(
                zip(memories, scores),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 提取排序后的记忆
            result = [memory for memory, score in reranked]
            
            # 如果指定了 top_k，只返回前 K 条
            if top_k is not None:
                result = result[:top_k]
            
            logger.info(
                f"重排序完成：{len(memories)} -> {len(result)} 条记忆"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"重排序失败：{e}", exc_info=True)
            return memories
    
    def _build_rerank_prompt(
        self,
        memories: List[MemorySearchResult],
        query: str
    ) -> str:
        """构建重排序 Prompt
        
        Args:
            memories: 记忆列表
            query: 查询文本
        
        Returns:
            完整的 Prompt 文本
        """
        # 构建记忆列表文本
        memory_lines = []
        for i, memory in enumerate(memories, 1):
            content = memory.entry.content
            # 限制每条记忆的长度，避免 Prompt 过长
            if len(content) > 200:
                content = content[:200] + "..."
            memory_lines.append(f"{i}. {content}")
        
        memory_text = "\n".join(memory_lines)
        
        # 构建 Prompt
        prompt = f"""你是一个记忆相关性评估专家。请根据用户查询，对以下记忆进行相关性评分。

用户查询：{query}

记忆列表：
{memory_text}

请为每条记忆打分（0-10分），分数越高表示与查询越相关。
请严格按照以下格式输出，不要添加额外内容：
1. 评分：X
2. 评分：X
...

现在请开始评分："""
        
        return prompt
    
    def _parse_scores(self, response: str, expected_count: int) -> List[float]:
        """解析 LLM 返回的评分
        
        Args:
            response: LLM 返回的文本
            expected_count: 预期的评分数量
        
        Returns:
            评分列表（浮点数）
        """
        scores: List[float] = []
        
        # 使用正则表达式匹配评分
        # 支持格式：1. 评分：8  或  1. 评分：8.5
        pattern = r"(\d+)\.\s*评分[：:]\s*(\d+(?:\.\d+)?)"
        matches = re.findall(pattern, response)
        
        # 提取分数
        for idx_str, score_str in matches:
            try:
                idx = int(idx_str)
                score = float(score_str)
                
                # 验证分数范围
                score = max(0.0, min(10.0, score))
                
                # 确保 scores 列表长度匹配
                while len(scores) < idx:
                    scores.append(5.0)  # 默认分数
                
                if idx == len(scores) + 1:
                    scores.append(score)
            
            except (ValueError, IndexError):
                continue
        
        # 如果解析失败，使用默认分数
        while len(scores) < expected_count:
            scores.append(5.0)
        
        # 截断到预期数量
        scores = scores[:expected_count]
        
        logger.debug(f"解析评分：{scores}")
        return scores
