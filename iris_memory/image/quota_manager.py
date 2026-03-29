"""
Iris Tier Memory - 图片解析配额管理组件

管理全局图片解析配额，支持每日自动重置。
"""

from datetime import datetime, date
from typing import TYPE_CHECKING
import asyncio

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .models import QuotaStatus

if TYPE_CHECKING:
    from astrbot.api.star import Context

logger = get_logger("image")


class ImageQuotaManager(Component):
    """图片解析配额管理组件
    
    管理全局图片解析配额，支持每日自动重置。
    使用 AstrBot KV 存储持久化配额状态。
    
    配额存储键：image_parsing_quota
    
    数据结构：
        {
            "date": "2026-03-29",      # 当前日期
            "used": 15,                 # 已使用次数
            "total": 200                # 总配额
        }
    
    Attributes:
        _context: AstrBot Context 对象
        _is_available: 组件是否可用
        _lock: 异步锁（防止并发竞争）
        _quota_status: 配额状态（内存缓存）
    
    Examples:
        >>> manager = ImageQuotaManager(context)
        >>> await manager.initialize()
        >>> if await manager.check_quota():
        ...     await manager.use_quota()
        ...     # 执行图片解析
    """
    
    # KV 存储键名
    KV_KEY = "image_parsing_quota"
    
    def __init__(self, context: "Context"):
        """初始化配额管理器
        
        Args:
            context: AstrBot Context 对象
        """
        self._context = context
        self._is_available = False
        self._lock = asyncio.Lock()
        self._quota_status: QuotaStatus | None = None
    
    @property
    def name(self) -> str:
        """组件名称"""
        return "image_quota"
    
    async def initialize(self) -> None:
        """初始化配额管理器"""
        config = get_config()
        
        # 检查是否启用
        if not config.get("image_parsing.enable"):
            self._is_available = False
            logger.info("图片解析未启用")
            return
        
        # 加载配额状态
        await self._load_quota_status()
        
        self._is_available = True
        logger.info(
            f"图片解析配额管理器初始化完成，"
            f"配额：{self._quota_status.used}/{self._quota_status.total}"
        )
    
    async def shutdown(self) -> None:
        """关闭配额管理器"""
        self._is_available = False
        logger.info("图片解析配额管理器已关闭")
    
    # ========================================================================
    # 配额状态管理
    # ========================================================================
    
    async def _load_quota_status(self) -> None:
        """从 KV 存储加载配额状态"""
        try:
            data = await self._context.get_kv_data(self.KV_KEY, {})
            
            if data:
                self._quota_status = QuotaStatus.from_dict(data)
                logger.debug(f"从 KV 存储加载配额状态：{self._quota_status.date}")
                
                # 检查是否需要重置（跨天）
                await self._check_and_reset_if_needed()
            else:
                # 首次使用，创建初始状态
                await self._create_initial_status()
        
        except Exception as e:
            logger.warning(f"从 KV 存储加载配额状态失败：{e}")
            # 创建初始状态
            await self._create_initial_status()
    
    async def _create_initial_status(self) -> None:
        """创建初始配额状态"""
        config = get_config()
        total = config.get("image_parsing.daily_quota", 200)
        today = date.today().isoformat()
        
        self._quota_status = QuotaStatus(
            date=today,
            used=0,
            total=total,
            last_reset_time=datetime.now()
        )
        
        await self._save_quota_status()
        logger.info(f"创建初始配额状态：{today}, total={total}")
    
    async def _save_quota_status(self) -> None:
        """保存配额状态到 KV 存储"""
        if not self._quota_status:
            return
        
        try:
            data = self._quota_status.to_dict()
            await self._context.put_kv_data(self.KV_KEY, data)
            logger.debug(f"保存配额状态：{self._quota_status.date}, used={self._quota_status.used}")
        
        except Exception as e:
            logger.warning(f"保存配额状态到 KV 存储失败：{e}")
    
    async def _check_and_reset_if_needed(self) -> None:
        """检查是否需要重置配额（跨天）"""
        if not self._quota_status:
            return
        
        today = date.today().isoformat()
        
        if self._quota_status.date != today:
            logger.info(
                f"检测到日期变更，重置配额："
                f"{self._quota_status.date} → {today}"
            )
            await self.reset_quota()
    
    # ========================================================================
    # 配额操作
    # ========================================================================
    
    async def check_quota(self) -> bool:
        """检查配额是否充足
        
        检查前会自动检测是否需要重置配额。
        
        Returns:
            配额是否充足
        
        Examples:
            >>> if await manager.check_quota():
            ...     await manager.use_quota()
        """
        if not self._is_available:
            return False
        
        async with self._lock:
            # 检查是否需要重置
            await self._check_and_reset_if_needed()
            
            if not self._quota_status:
                return False
            
            return not self._quota_status.is_exhausted
    
    async def use_quota(self, count: int = 1) -> bool:
        """使用配额
        
        原子操作：检查配额并扣减。
        
        Args:
            count: 使用数量（默认 1）
        
        Returns:
            是否成功使用
        
        Examples:
            >>> success = await manager.use_quota(2)
            >>> if success:
            ...     # 执行图片解析
            ...     pass
        """
        if not self._is_available:
            return False
        
        async with self._lock:
            # 检查是否需要重置
            await self._check_and_reset_if_needed()
            
            if not self._quota_status:
                return False
            
            # 检查配额是否充足
            if self._quota_status.used + count > self._quota_status.total:
                logger.warning(
                    f"配额不足：used={self._quota_status.used}, "
                    f"total={self._quota_status.total}, request={count}"
                )
                return False
            
            # 扣减配额
            self._quota_status.used += count
            await self._save_quota_status()
            
            logger.debug(
                f"使用配额成功：count={count}, "
                f"used={self._quota_status.used}/{self._quota_status.total}"
            )
            
            return True
    
    async def reset_quota(self) -> None:
        """重置配额
        
        将使用次数归零，更新日期为今天。
        
        Examples:
            >>> await manager.reset_quota()
        """
        async with self._lock:
            if not self._quota_status:
                await self._create_initial_status()
                return
            
            config = get_config()
            today = date.today().isoformat()
            
            # 重置状态
            self._quota_status.date = today
            self._quota_status.used = 0
            self._quota_status.total = config.get("image_parsing.daily_quota", 200)
            self._quota_status.last_reset_time = datetime.now()
            
            await self._save_quota_status()
            logger.info(f"配额已重置：{today}, total={self._quota_status.total}")
    
    # ========================================================================
    # 状态查询
    # ========================================================================
    
    async def get_status(self) -> QuotaStatus | None:
        """获取当前配额状态
        
        Returns:
            配额状态对象
        
        Examples:
            >>> status = await manager.get_status()
            >>> print(f"剩余配额：{status.remaining}")
        """
        if not self._is_available:
            return None
        
        async with self._lock:
            await self._check_and_reset_if_needed()
            return self._quota_status
    
    @property
    def is_available(self) -> bool:
        """组件是否可用"""
        return self._is_available and self._quota_status is not None
