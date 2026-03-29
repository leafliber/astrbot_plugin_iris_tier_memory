"""
Iris Tier Memory - LLM 调用管理器

提供统一的 LLM 调用入口，支持 Token 统计与调用追踪。
"""

from typing import Optional, Dict, List, Any, TYPE_CHECKING
from datetime import datetime
from collections import deque
import uuid
import time

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .token_stats import TokenStatsManager
from .call_log import CallLog

if TYPE_CHECKING:
    from astrbot.api.star import Context
    from astrbot.api.provider import LLMResponse

logger = get_logger("llm_manager")


class LLMManager(Component):
    """LLM 调用管理器
    
    提供统一的 LLM 调用入口，支持：
    - Token 统计与持久化（AstrBot KV 存储）
    - 调用日志记录（内存存储）
    - 模块级 Provider 配置
    - 调用追踪
    
    Attributes:
        _context: AstrBot Context 对象
        _token_stats: Token 统计管理器
        _call_logs: 调用日志队列
    
    Examples:
        >>> manager = LLMManager(context)
        >>> await manager.initialize()
        >>> response = await manager.generate(
        ...     prompt="Hello",
        ...     module="l1_summarizer"
        ... )
    """
    
    def __init__(self, context: "Context"):
        """初始化管理器
        
        Args:
            context: AstrBot Context 对象
        """
        super().__init__()
        self._context = context
        self._token_stats: Optional[TokenStatsManager] = None
        self._call_logs: deque[CallLog] = deque(maxlen=100)
    
    @property
    def name(self) -> str:
        """组件名称"""
        return "llm_manager"
    
    async def initialize(self) -> None:
        """初始化管理器
        
        创建 Token 统计管理器，加载配置。
        """
        try:
            config = get_config()
            
            # 初始化 Token 统计管理器
            self._token_stats = TokenStatsManager(self._context)
            
            # 加载调用日志最大条数配置
            # 注意：隐藏配置使用单层键名，不需要 "hidden." 前缀
            max_logs = config.get("call_log_max_entries", 100)
            self._call_logs = deque(maxlen=max_logs)
            
            self._is_available = True
            logger.info("LLMManager 初始化成功")
        
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"LLMManager 初始化失败：{e}", exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """关闭管理器"""
        self._is_available = False
        logger.info("LLMManager 已关闭")
    
    # =========================================================================
    # 核心方法
    # =========================================================================
    
    async def generate(
        self,
        prompt: str,
        module: str = "default",
        provider_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        contexts: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """生成文本响应
        
        Args:
            prompt: 输入提示词
            module: 调用模块标识（用于统计），如 "l1_summarizer"
            provider_id: Provider ID（留空使用模块配置或默认）
            temperature: 温度参数（暂不支持，AstrBot 内部处理）
            max_tokens: 最大输出 Token 数（暂不支持，AstrBot 内部处理）
            contexts: 上下文消息列表
            **kwargs: 其他参数
        
        Returns:
            生成的文本响应
        
        Raises:
            RuntimeError: LLMManager 未初始化
            Exception: LLM 调用失败
        
        Examples:
            >>> response = await manager.generate(
            ...     prompt="Hello",
            ...     module="l1_summarizer"
            ... )
        """
        if not self._is_available:
            raise RuntimeError("LLMManager 未初始化")
        
        # 确定使用的 provider
        actual_provider_id = await self._resolve_provider(module, provider_id)
        
        # 记录开始时间
        start_time = time.time()
        call_id = str(uuid.uuid4())
        
        try:
            logger.debug(
                f"LLM 调用开始：module={module}, provider={actual_provider_id or 'default'}"
            )
            
            # 调用 AstrBot LLM
            llm_resp: "LLMResponse" = await self._context.llm_generate(
                chat_provider_id=actual_provider_id,
                prompt=prompt,
                contexts=contexts or [],
            )
            
            # 提取响应
            response_text = llm_resp.completion_text or ""
            
            # 计算耗时
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录 Token 使用
            input_tokens = llm_resp.usage.prompt_tokens if llm_resp.usage else 0
            output_tokens = llm_resp.usage.completion_tokens if llm_resp.usage else 0
            
            if self._token_stats:
                await self._token_stats.record_usage(
                    module=module,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            
            # 记录调用日志
            log = CallLog(
                call_id=call_id,
                timestamp=datetime.now(),
                module=module,
                provider_id=actual_provider_id or "default",
                prompt=self._truncate_text(prompt, 500),
                response=self._truncate_text(response_text, 500),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=True
            )
            self._call_logs.append(log)
            
            logger.info(
                f"LLM 调用成功：module={module}, "
                f"tokens={input_tokens}+{output_tokens}, "
                f"duration={duration_ms}ms"
            )
            
            return response_text
        
        except Exception as e:
            # 记录失败日志
            duration_ms = int((time.time() - start_time) * 1000)
            log = CallLog(
                call_id=call_id,
                timestamp=datetime.now(),
                module=module,
                provider_id=actual_provider_id or "default",
                prompt=self._truncate_text(prompt, 500),
                response="",
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
            self._call_logs.append(log)
            
            logger.error(f"LLM 调用失败：module={module}, error={e}")
            raise
    
    async def _resolve_provider(
        self,
        module: str,
        provider_id: Optional[str]
    ) -> str:
        """解析要使用的 Provider ID
        
        优先级：参数 > 模块配置 > 默认（空字符串）
        
        Args:
            module: 模块名
            provider_id: 参数传入的 provider_id
        
        Returns:
            实际使用的 Provider ID
        """
        if provider_id:
            return provider_id
        
        # 从配置获取模块对应的 provider
        config = get_config()
        
        # 模块名到配置键的映射
        module_config_map = {
            "l1_summarizer": "l1_buffer.summary_provider",
            "l2_summarizer": "l2_memory.summary_provider",
            "l3_kg_extraction": "l3_kg.extraction_provider",
            "scheduled_tasks": "scheduled_tasks.provider",
            "enhancement_rerank": "enhancement.rerank_provider",
            "image_parsing": "image_parsing.provider",
        }
        
        config_key = module_config_map.get(module)
        if config_key:
            configured_provider = config.get(config_key)
            if configured_provider:
                return configured_provider
        
        # 返回空字符串，使用默认 provider
        return ""
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
        
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    # =========================================================================
    # LLMCaller 协议接口
    # =========================================================================
    
    async def call(self, prompt: str, provider: str = "") -> str:
        """调用 LLM 生成响应（LLMCaller 协议接口）
        
        为兼容现有代码提供简化接口。
        
        Args:
            prompt: 输入提示词
            provider: Provider ID
        
        Returns:
            生成的文本响应
        
        Examples:
            >>> response = await manager.call("Hello", provider="gpt-4o")
        """
        return await self.generate(
            prompt=prompt,
            module="default",
            provider_id=provider if provider else None
        )
    
    # =========================================================================
    # 统计接口
    # =========================================================================
    
    async def get_token_stats(self, module: str = "global") -> Dict[str, Any]:
        """获取 Token 统计
        
        Args:
            module: 模块名（默认 "global"）
        
        Returns:
            统计信息字典
        
        Examples:
            >>> stats = await manager.get_token_stats("l1_summarizer")
            >>> print(stats["total_tokens"])
        """
        if not self._token_stats:
            return {
                "module": module,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_calls": 0
            }
        
        usage = await self._token_stats.get_stats(module)
        return {
            "module": module,
            "total_input_tokens": usage.total_input_tokens,
            "total_output_tokens": usage.total_output_tokens,
            "total_calls": usage.total_calls
        }
    
    async def get_all_token_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模块的 Token 统计
        
        Returns:
            模块名到统计信息的映射
        
        Examples:
            >>> all_stats = await manager.get_all_token_stats()
            >>> for module, stats in all_stats.items():
            ...     print(f"{module}: {stats['total_tokens']}")
        """
        if not self._token_stats:
            return {}
        
        all_stats = await self._token_stats.get_all_stats()
        return {
            module: {
                "total_input_tokens": usage.total_input_tokens,
                "total_output_tokens": usage.total_output_tokens,
                "total_calls": usage.total_calls
            }
            for module, usage in all_stats.items()
        }
    
    async def reset_token_stats(self, module: str = "global") -> None:
        """重置 Token 统计
        
        Args:
            module: 模块名（默认 "global"）
        
        Examples:
            >>> await manager.reset_token_stats("l1_summarizer")
        """
        if self._token_stats:
            await self._token_stats.reset_stats(module)
            logger.info(f"已重置 Token 统计：{module}")
    
    def get_recent_call_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的调用日志
        
        Args:
            limit: 返回数量（默认 20）
        
        Returns:
            调用日志列表
        
        Examples:
            >>> logs = manager.get_recent_call_logs(10)
            >>> for log in logs:
            ...     print(f"{log['module']}: {log['duration_ms']}ms")
        """
        logs = list(self._call_logs)[-limit:]
        return [
            {
                "call_id": log.call_id,
                "timestamp": log.timestamp.isoformat(),
                "module": log.module,
                "provider_id": log.provider_id,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "duration_ms": log.duration_ms,
                "success": log.success,
                "error_message": log.error_message
            }
            for log in logs
        ]
