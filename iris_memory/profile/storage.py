"""
Iris Tier Memory - 画像存储组件

使用 AstrBot KV 存储 API 实现画像数据持久化。
支持群聊隔离和人格隔离。
"""

from typing import Optional, TYPE_CHECKING

from iris_memory.core import Component, get_logger
from iris_memory.core.storage import KVStorage
from iris_memory.config import get_config
from .models import (
    GroupProfile,
    UserProfile,
    profile_to_dict,
    dict_to_group_profile,
    dict_to_user_profile
)

if TYPE_CHECKING:
    pass

logger = get_logger("profile")


class ProfileStorage(Component):
    """画像存储组件
    
    使用 AstrBot KV 存储 API，支持群聊隔离和人格隔离。
    
    存储键格式：
        - 群聊画像：group_profile:{persona_id}:{group_id}
        - 用户画像：user_profile:{persona_id}:{group_id}:{user_id}
    
    Attributes:
        _storage: KV 存储适配器
        _is_available: 组件是否可用
    """
    
    def __init__(self, storage: KVStorage):
        """初始化画像存储组件
        
        Args:
            storage: KV 存储适配器（实现 KVStorage 协议的对象）
        """
        super().__init__()
        self._storage = storage
    
    @property
    def name(self) -> str:
        """组件名称"""
        return "profile"
    
    async def initialize(self) -> None:
        """初始化画像存储"""
        config = get_config()
        
        if not config.get("profile.enable"):
            self._is_available = False
            logger.info("画像系统未启用")
            return
        
        self._is_available = True
        logger.info("画像存储组件初始化完成")
    
    async def shutdown(self) -> None:
        """关闭存储"""
        self._reset_state()
        logger.info("画像存储组件已关闭")
    
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
        """
        if not self._is_available:
            return None
        
        key = f"group_profile:{persona_id}:{group_id}"
        
        try:
            data = await self._storage.get_kv_data(key, None)
            
            if data:
                profile = dict_to_group_profile(data)
                logger.debug(f"获取群聊画像成功: {key}")
                return profile
            
            logger.debug(f"群聊画像不存在: {key}")
            return None
        
        except Exception as e:
            logger.error(f"获取群聊画像失败: {key}, 错误: {e}")
            return None
    
    async def save_group_profile(self, profile: GroupProfile, increment_version: bool = True) -> None:
        if not self._is_available:
            return
        
        if increment_version:
            profile.version += 1
        
        persona_id = self._get_persona_id()
        key = f"group_profile:{persona_id}:{profile.group_id}"
        
        try:
            data = profile_to_dict(profile)
            await self._storage.put_kv_data(key, data)
            await self._add_to_group_index(profile.group_id, persona_id)
            logger.debug(f"保存群聊画像成功: {key}, version={profile.version}")
        
        except Exception as e:
            logger.error(f"保存群聊画像失败: {key}, 错误: {e}")
    
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
        """
        if not self._is_available:
            return None
        
        key = f"user_profile:{persona_id}:{group_id}:{user_id}"
        
        try:
            data = await self._storage.get_kv_data(key, None)
            
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
        group_id: str = "default",
        increment_version: bool = True
    ) -> None:
        if not self._is_available:
            return
        
        if increment_version:
            profile.version += 1
        
        persona_id = self._get_persona_id()
        key = f"user_profile:{persona_id}:{group_id}:{profile.user_id}"
        
        try:
            data = profile_to_dict(profile)
            await self._storage.put_kv_data(key, data)
            await self._add_to_user_index(profile.user_id, group_id, persona_id)
            logger.debug(f"保存用户画像成功: {key}, version={profile.version}")
        
        except Exception as e:
            logger.error(f"保存用户画像失败: {key}, 错误: {e}")
    
    def _get_persona_id(self) -> str:
        """获取当前人格ID
        
        Returns:
            人格ID，未启用人格隔离则返回 "default"
        """
        config = get_config()
        if config.get("isolation_config.enable_persona_isolation"):
            return "default"
        
        return "default"
    
    async def update_group_profile(
        self, 
        group_id: str, 
        updates: dict
    ) -> bool:
        """更新群聊画像
        
        Args:
            group_id: 群聊ID
            updates: 更新字段字典
        
        Returns:
            是否更新成功
        """
        try:
            profile = await self.get_group_profile(group_id)
            
            if not profile:
                profile = GroupProfile(group_id=group_id)
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            await self.save_group_profile(profile)
            logger.info(f"更新群聊画像成功: {group_id}")
            return True
        
        except Exception as e:
            logger.error(f"更新群聊画像失败: {e}", exc_info=True)
            return False
    
    async def update_user_profile(
        self, 
        user_id: str, 
        group_id: str,
        updates: dict
    ) -> bool:
        """更新用户画像
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
            updates: 更新字段字典
        
        Returns:
            是否更新成功
        """
        try:
            profile = await self.get_user_profile(user_id, group_id)
            
            if not profile:
                profile = UserProfile(user_id=user_id)
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            await self.save_user_profile(profile, group_id)
            logger.info(f"更新用户画像成功: {user_id}@{group_id}")
            return True
        
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}", exc_info=True)
            return False
    
    async def list_groups(self) -> list:
        persona_id = self._get_persona_id()
        index_key = f"group_index:{persona_id}"
        
        try:
            group_ids = await self._storage.get_kv_data(index_key, [])
            
            groups = []
            for group_id in group_ids:
                profile = await self.get_group_profile(group_id)
                if profile:
                    groups.append({
                        "group_id": group_id,
                        "group_name": profile.group_name or group_id,
                        "member_count": len(profile.active_users) if profile.active_users else 0
                    })
            
            return groups
        
        except Exception as e:
            logger.error(f"获取群聊列表失败: {e}", exc_info=True)
            return []
    
    async def list_users(self, group_id: str = "default") -> list:
        persona_id = self._get_persona_id()
        index_key = f"user_index:{persona_id}:{group_id}"
        
        try:
            user_ids = await self._storage.get_kv_data(index_key, [])
            
            users = []
            for user_id in user_ids:
                profile = await self.get_user_profile(user_id, group_id)
                if profile:
                    users.append({
                        "user_id": user_id,
                        "nickname": profile.user_name or user_id,
                        "group_id": group_id
                    })
            
            return users
        
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            return []
    
    async def _add_to_group_index(self, group_id: str, persona_id: str) -> None:
        index_key = f"group_index:{persona_id}"
        try:
            group_ids = await self._storage.get_kv_data(index_key, [])
            if group_id not in group_ids:
                group_ids.append(group_id)
                await self._storage.put_kv_data(index_key, group_ids)
        except Exception as e:
            logger.error(f"更新群聊索引失败: {e}")
    
    async def _add_to_user_index(self, user_id: str, group_id: str, persona_id: str) -> None:
        index_key = f"user_index:{persona_id}:{group_id}"
        try:
            user_ids = await self._storage.get_kv_data(index_key, [])
            if user_id not in user_ids:
                user_ids.append(user_id)
                await self._storage.put_kv_data(index_key, user_ids)
        except Exception as e:
            logger.error(f"更新用户索引失败: {e}")
    
    async def delete_user_profile(
        self,
        user_id: str,
        group_id: str = "default"
    ) -> bool:
        """删除用户画像
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID
        
        Returns:
            是否删除成功
        """
        if not self._is_available:
            return False
        
        persona_id = self._get_persona_id()
        key = f"user_profile:{persona_id}:{group_id}:{user_id}"
        
        try:
            await self._storage.delete_kv_data(key)
            logger.info(f"已删除用户画像: {key}")
            return True
        
        except Exception as e:
            logger.error(f"删除用户画像失败: {key}, 错误: {e}")
            return False
    
    async def delete_group_profile(self, group_id: str) -> bool:
        """删除群聊画像
        
        Args:
            group_id: 群聊ID
        
        Returns:
            是否删除成功
        """
        if not self._is_available:
            return False
        
        persona_id = self._get_persona_id()
        key = f"group_profile:{persona_id}:{group_id}"
        
        try:
            await self._storage.delete_kv_data(key)
            logger.info(f"已删除群聊画像: {key}")
            return True
        
        except Exception as e:
            logger.error(f"删除群聊画像失败: {key}, 错误: {e}")
            return False
    
    async def delete_all_user_profiles_in_group(self, group_id: str) -> int:
        """删除群聊内所有用户画像
        
        注意：此方法需要遍历所有键，效率较低。
        当前实现为占位符，需要 AstrBot KV 存储支持列表功能。
        
        Args:
            group_id: 群聊ID
        
        Returns:
            删除的画像数量
        """
        logger.warning("delete_all_user_profiles_in_group 需要 AstrBot KV 存储支持列表功能")
        return 0
    
    async def delete_all_user_profiles(self) -> int:
        """删除所有用户画像
        
        注意：此方法需要遍历所有键，效率较低。
        当前实现为占位符，需要 AstrBot KV 存储支持列表功能。
        
        Returns:
            删除的画像数量
        """
        logger.warning("delete_all_user_profiles 需要 AstrBot KV 存储支持列表功能")
        return 0
    
    async def delete_all_group_profiles(self) -> int:
        """删除所有群聊画像
        
        注意：此方法需要遍历所有键，效率较低。
        当前实现为占位符，需要 AstrBot KV 存储支持列表功能。
        
        Returns:
            删除的画像数量
        """
        logger.warning("delete_all_group_profiles 需要 AstrBot KV 存储支持列表功能")
        return 0
    
    async def delete_all_profiles(self) -> dict:
        """删除所有画像（用户画像 + 群聊画像）
        
        Returns:
            删除统计 {"user_profiles": int, "group_profiles": int}
        """
        user_count = await self.delete_all_user_profiles()
        group_count = await self.delete_all_group_profiles()
        
        return {
            "user_profiles": user_count,
            "group_profiles": group_count
        }
