"""
Iris Tier Memory - 画像存储组件

使用 AstrBot KV 存储 API 实现画像数据持久化。
支持群聊隔离和人格隔离。
"""

from typing import Optional, TYPE_CHECKING

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .models import (
    GroupProfile,
    UserProfile,
    profile_to_dict,
    dict_to_group_profile,
    dict_to_user_profile
)

if TYPE_CHECKING:
    from astrbot.core.platform import AstrBotContext

logger = get_logger("profile")


# ============================================================================
# 画像存储组件
# ============================================================================

class ProfileStorage(Component):
    """画像存储组件
    
    使用 AstrBot KV 存储 API，支持群聊隔离和人格隔离。
    
    存储键格式：
        - 群聊画像：group_profile:{persona_id}:{group_id}
        - 用户画像：user_profile:{persona_id}:{group_id}:{user_id}
    
    Attributes:
        _context: AstrBot 上下文对象
        _is_available: 组件是否可用
    
    Examples:
        >>> storage = ProfileStorage(context)
        >>> await storage.initialize()
        >>> profile = await storage.get_group_profile("group_123")
    """
    
    def __init__(self, context: "AstrBotContext"):
        """初始化画像存储组件
        
        Args:
            context: AstrBot 上下文对象
        """
        self._context = context
        self._is_available = False
    
    @property
    def name(self) -> str:
        """组件名称"""
        return "profile"
    
    async def initialize(self) -> None:
        """初始化画像存储"""
        config = get_config()
        
        # 检查是否启用
        if not config.get("profile.enable"):
            self._is_available = False
            logger.info("画像系统未启用")
            return
        
        self._is_available = True
        logger.info("画像存储组件初始化完成")
    
    async def shutdown(self) -> None:
        """关闭存储"""
        self._is_available = False
        logger.info("画像存储组件已关闭")
    
    # ========================================================================
    # 群聊画像操作
    # ========================================================================
    
    async def get_group_profile(
        self, 
        group_id: str, 
        persona_id: str = "default"
    ) -> Optional[GroupProfile]:
        """获取群聊画像
        
        Args:
            group_id: 群聊ID
            persona_id: 人格ID（默认为 "default"）
        
        Returns:
            群聊画像对象，不存在则返回 None
        
        Examples:
            >>> profile = await storage.get_group_profile("group_123")
            >>> if profile:
            ...     print(profile.group_name)
        """
        if not self._is_available:
            return None
        
        key = f"group_profile:{persona_id}:{group_id}"
        
        try:
            data = await self._context.get_kv_data(key)
            
            if data:
                profile = dict_to_group_profile(data)
                logger.debug(f"获取群聊画像成功: {key}")
                return profile
            
            logger.debug(f"群聊画像不存在: {key}")
            return None
        
        except Exception as e:
            logger.error(f"获取群聊画像失败: {key}, 错误: {e}")
            return None
    
    async def save_group_profile(self, profile: GroupProfile) -> None:
        """保存群聊画像
        
        Args:
            profile: 群聊画像对象
        
        Examples:
            >>> profile = GroupProfile(group_id="group_123")
            >>> await storage.save_group_profile(profile)
        """
        if not self._is_available:
            return
        
        # 更新版本号
        profile.version += 1
        
        # 获取人格ID
        persona_id = self._get_persona_id()
        key = f"group_profile:{persona_id}:{profile.group_id}"
        
        try:
            data = profile_to_dict(profile)
            await self._context.put_kv_data(key, data)
            logger.debug(f"保存群聊画像成功: {key}, version={profile.version}")
        
        except Exception as e:
            logger.error(f"保存群聊画像失败: {key}, 错误: {e}")
    
    # ========================================================================
    # 用户画像操作
    # ========================================================================
    
    async def get_user_profile(
        self,
        user_id: str,
        group_id: str = "default",
        persona_id: str = "default"
    ) -> Optional[UserProfile]:
        """获取用户画像
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID（全局模式传 "default"）
            persona_id: 人格ID（默认为 "default"）
        
        Returns:
            用户画像对象，不存在则返回 None
        
        Examples:
            >>> profile = await storage.get_user_profile("user_456", "group_123")
            >>> if profile:
            ...     print(profile.user_name)
        """
        if not self._is_available:
            return None
        
        # 统一键格式：user_profile:{persona_id}:{group_id}:{user_id}
        key = f"user_profile:{persona_id}:{group_id}:{user_id}"
        
        try:
            data = await self._context.get_kv_data(key)
            
            if data:
                profile = dict_to_user_profile(data)
                logger.debug(f"获取用户画像成功: {key}")
                return profile
            
            logger.debug(f"用户画像不存在: {key}")
            return None
        
        except Exception as e:
            logger.error(f"获取用户画像失败: {key}, 错误: {e}")
            return None
    
    async def save_user_profile(
        self, 
        profile: UserProfile,
        group_id: str = "default"
    ) -> None:
        """保存用户画像
        
        Args:
            profile: 用户画像对象
            group_id: 群聊ID（全局模式传 "default"）
        
        Examples:
            >>> profile = UserProfile(user_id="user_456")
            >>> await storage.save_user_profile(profile, "group_123")
        """
        if not self._is_available:
            return
        
        # 更新版本号
        profile.version += 1
        
        # 统一键格式
        persona_id = self._get_persona_id()
        key = f"user_profile:{persona_id}:{group_id}:{profile.user_id}"
        
        try:
            data = profile_to_dict(profile)
            await self._context.put_kv_data(key, data)
            logger.debug(f"保存用户画像成功: {key}, version={profile.version}")
        
        except Exception as e:
            logger.error(f"保存用户画像失败: {key}, 错误: {e}")
    
    # ========================================================================
    # 辅助方法
    # ========================================================================
    
    def _get_persona_id(self) -> str:
        """获取当前人格ID
        
        根据人格隔离配置返回人格ID。
        
        Returns:
            人格ID，未启用人格隔离则返回 "default"
        """
        config = get_config()
        if config.get("isolation_config.enable_persona_isolation"):
            # 从上下文获取当前人格ID
            # TODO: 实现从 context 获取 persona_id 的逻辑
            # 目前返回默认值
            return getattr(self._context, 'persona_id', 'default')
        return "default"
