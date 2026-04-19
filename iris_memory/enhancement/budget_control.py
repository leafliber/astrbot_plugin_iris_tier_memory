"""
Iris Tier Memory - Token 预算控制器

根据 Token 预算控制注入记忆的数量，防止上下文溢出。
支持字符估算和可选的真实 tokenizer。
"""

from typing import List, Optional, Tuple
from iris_memory.core import get_logger
from iris_memory.config import get_config
from iris_memory.l2_memory.models import MemorySearchResult

logger = get_logger("enhancement.budget_control")


class TokenBudgetController:
    """Token 预算控制器
    
    根据设置的 Token 预算，计算并控制注入记忆的数量，防止溢出。
    
    Features:
        - Token 估算（字符估算 + 可选真实 tokenizer）
        - 记忆列表裁剪
        - 预算分配策略
    
    Attributes:
        max_tokens: 最大 Token 预算
    
    Examples:
        >>> controller = TokenBudgetController(max_tokens=2000)
        >>> trimmed = controller.trim_memories(memories)
        >>> print(f"注入 {len(trimmed)} 条记忆")
    """
    
    def __init__(self, max_tokens: Optional[int] = None):
        """初始化控制器
        
        Args:
            max_tokens: 最大 Token 预算，留空从配置读取
        """
        if max_tokens is not None:
            self.max_tokens = max_tokens
        else:
            config = get_config()
            self.max_tokens = config.get("token_budget_max_tokens", 2000)
        
        # 可选：尝试加载 tiktoken（真实 tokenizer）
        self._tokenizer = None
        self._use_real_tokenizer = False
        
        # 尝试加载 tiktoken（可选依赖）
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4/3.5 编码
            self._use_real_tokenizer = True
            logger.debug("已加载 tiktoken 真实 tokenizer")
        except ImportError:
            logger.debug("tiktoken 未安装，使用字符估算")
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数
        
        优先使用真实 tokenizer，否则使用字符估算。
        
        Args:
            text: 文本内容
        
        Returns:
            估算的 Token 数
        
        Examples:
            >>> controller = TokenBudgetController()
            >>> tokens = controller.estimate_tokens("你好世界")
            >>> print(tokens)  # 约 2-4 tokens
        """
        if not text:
            return 0
        
        # 使用真实 tokenizer
        if self._use_real_tokenizer and self._tokenizer:
            return len(self._tokenizer.encode(text))
        
        # 字符估算（中文约 2 字符/token，英文约 4 字符/token）
        # 采用保守估算：平均 2 字符/token
        return len(text) // 2 + 1
    
    def trim_memories(
        self,
        memories: List[MemorySearchResult],
        max_tokens: Optional[int] = None,
        preserve_order: bool = True
    ) -> Tuple[List[MemorySearchResult], int]:
        """裁剪记忆列表以满足 Token 预算
        
        从前往后逐条添加记忆，直到超出预算。
        
        Args:
            memories: 记忆检索结果列表
            max_tokens: 最大 Token 预算（可选，默认使用初始化值）
            preserve_order: 是否保持原始顺序
        
        Returns:
            (裁剪后的记忆列表, 实际使用的 Token 数)
        
        Examples:
            >>> controller = TokenBudgetController(max_tokens=500)
            >>> trimmed, tokens = controller.trim_memories(memories)
            >>> print(f"注入 {len(trimmed)} 条记忆，共 {tokens} tokens")
        """
        if not memories:
            return [], 0
        
        budget = max_tokens or self.max_tokens
        trimmed: List[MemorySearchResult] = []
        total_tokens = 0
        
        for memory in memories:
            # 估算单条记忆的 Token 数
            content = memory.entry.content
            memory_tokens = self.estimate_tokens(content)
            
            # 检查是否超出预算
            if total_tokens + memory_tokens > budget:
                # 如果是第一条记忆且超出预算，仍然保留（避免空结果）
                if not trimmed:
                    trimmed.append(memory)
                    total_tokens = memory_tokens
                    logger.warning(
                        f"单条记忆超出预算：{memory_tokens} > {budget}，仍保留"
                    )
                break
            
            trimmed.append(memory)
            total_tokens += memory_tokens
        
        logger.debug(
            f"Token 预算裁剪：{len(memories)} -> {len(trimmed)} 条，"
            f"{total_tokens}/{budget} tokens"
        )
        
        return trimmed, total_tokens
    
    def estimate_total_tokens(self, memories: List[MemorySearchResult]) -> int:
        """估算记忆列表的总 Token 数
        
        Args:
            memories: 记忆检索结果列表
        
        Returns:
            总 Token 数
        
        Examples:
            >>> controller = TokenBudgetController()
            >>> total = controller.estimate_total_tokens(memories)
        """
        total = 0
        for memory in memories:
            total += self.estimate_tokens(memory.entry.content)
        return total
    
    def can_fit(
        self,
        memories: List[MemorySearchResult],
        additional_tokens: int = 0
    ) -> bool:
        """检查记忆列表是否在预算内
        
        Args:
            memories: 记忆检索结果列表
            additional_tokens: 额外预留的 Token 数
        
        Returns:
            是否在预算内
        
        Examples:
            >>> controller = TokenBudgetController(max_tokens=2000)
            >>> if controller.can_fit(memories, additional_tokens=500):
            ...     print("预算充足")
        """
        total = self.estimate_total_tokens(memories)
        return total + additional_tokens <= self.max_tokens
