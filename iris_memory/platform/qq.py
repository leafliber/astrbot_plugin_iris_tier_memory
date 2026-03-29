"""
Iris Tier Memory - OneBot11 平台适配器

实现 QQ 平台（OneBot11 协议）的适配器，从 AstrMessageEvent 提取平台信息。

OneBot11 协议参考：
- https://github.com/botuniverse/onebot-11

实现要点：
- 用户ID：event.sender.user_id
- 用户昵称：event.sender.nickname（群聊时优先使用 event.sender.card）
- 群ID：event.group_id（私聊为空字符串）
- 群名称：从 raw_message 提取（如果可用）
- 用户角色：event.sender.role（owner/admin/member）
"""

from typing import Any, List

from iris_memory.core import get_logger
from iris_memory.platform.base import PlatformAdapter

logger = get_logger("platform.qq")


class OneBot11Adapter(PlatformAdapter):
    """OneBot11 平台适配器
    
    实现 QQ 平台（OneBot11 协议）的消息信息提取。
    
    特性：
    - 支持群聊/私聊识别
    - 群聊时优先返回群名片
    - 支持角色识别（owner/admin/member）
    - 提供原始消息访问
    
    Examples:
        >>> adapter = OneBot11Adapter()
        >>> user_id = adapter.get_user_id(event)
        >>> group_id = adapter.get_group_id(event)
        >>> is_group = adapter.is_group_message(event)
    """
    
    def get_user_id(self, event: Any) -> str:
        """获取用户ID（QQ号）
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            QQ号字符串
        """
        try:
            return str(event.sender.user_id)
        except AttributeError:
            logger.error("无法获取用户ID：event.sender.user_id 不存在")
            raise
    
    def get_user_name(self, event: Any) -> str:
        """获取用户显示名称
        
        群聊时优先返回群名片（如果有），否则返回昵称。
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            用户显示名称
        """
        try:
            # 群聊时优先使用群名片
            if self.is_group_message(event):
                card = getattr(event.sender, "card", "")
                if card:
                    return str(card)
            
            # 否则返回昵称
            return str(event.sender.nickname)
        except AttributeError:
            logger.error("无法获取用户名称：event.sender 结构异常")
            raise
    
    def get_user_nickname(self, event: Any) -> str:
        """获取用户原始昵称
        
        不考虑群名片，始终返回原始昵称。
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            用户昵称
        """
        try:
            return str(event.sender.nickname)
        except AttributeError:
            logger.error("无法获取用户昵称：event.sender.nickname 不存在")
            raise
    
    def get_group_id(self, event: Any) -> str:
        """获取群聊ID（群号）
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            群号字符串，私聊时返回空字符串
        """
        try:
            group_id = getattr(event, "group_id", "")
            return str(group_id) if group_id else ""
        except AttributeError:
            logger.error("无法获取群ID：event.group_id 不存在")
            raise
    
    def get_group_name(self, event: Any) -> str:
        """获取群聊名称
        
        尝试从原始消息中提取群名称信息。
        OneBot11 协议中，群名称通常不在消息事件中提供，
        需要通过专门的 API 调用获取。
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            群名称字符串，无法获取时返回空字符串
        """
        try:
            # 尝试从原始消息提取群名称（通常不可用）
            raw_msg = self.get_raw_message(event)
            
            # OneBot11 消息格式中可能包含群名称
            if "group_name" in raw_msg:
                return str(raw_msg["group_name"])
            
            # 某些实现可能在 sender 中提供
            if hasattr(event, "sender") and hasattr(event.sender, "group_name"):
                return str(event.sender.group_name)
            
            # 无法获取时返回空字符串
            return ""
        except Exception as e:
            logger.debug(f"无法获取群名称: {e}")
            return ""
    
    def get_user_role(self, event: Any) -> str:
        """获取用户在群聊中的角色
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            角色字符串：owner、admin、member、private
        """
        try:
            # 私聊时返回 private
            if not self.is_group_message(event):
                return "private"
            
            # 群聊时获取角色
            role = getattr(event.sender, "role", "member")
            return str(role)
        except AttributeError:
            logger.error("无法获取用户角色：event.sender.role 不存在")
            raise
    
    def get_raw_message(self, event: Any) -> dict[str, Any]:
        """获取平台原始消息对象
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            原始消息字典，解析失败时返回空字典
        """
        try:
            # 尝试获取 raw_message
            raw_msg = getattr(event, "raw_message", None)
            
            # 如果 raw_message 不存在，尝试从 message_obj 获取
            if raw_msg is None and hasattr(event, "message_obj"):
                raw_msg = getattr(event.message_obj, "raw_message", None)
            
            # 转换为字典
            if raw_msg is None:
                logger.debug("原始消息对象为空")
                return {}
            
            # 如果已经是字典，直接返回
            if isinstance(raw_msg, dict):
                return raw_msg
            
            # 如果是对象，尝试转为字典
            if hasattr(raw_msg, "__dict__"):
                return raw_msg.__dict__
            
            # 其他情况返回空字典
            logger.debug(f"无法解析原始消息对象: {type(raw_msg)}")
            return {}
        except Exception as e:
            logger.error(f"获取原始消息失败: {e}")
            return {}
    
    def is_group_message(self, event: "AstrMessageEvent") -> bool:
        """判断是否为群聊消息
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            True 表示群聊消息，False 表示私聊消息
        """
        try:
            group_id = self.get_group_id(event)
            return bool(group_id)
        except Exception:
            return False
    
    def get_images(self, event: Any) -> List["ImageInfo"]:
        """获取消息中的图片列表
        
        从 OneBot11 消息段中提取图片信息。
        支持提取：
        - 当前消息中的图片
        - 引用/回复消息中的图片
        
        Args:
            event: AstrBot 消息事件对象
        
        Returns:
            图片信息列表
        """
        from iris_memory.image.models import ImageInfo
        
        images: List[ImageInfo] = []
        
        try:
            # 获取原始消息
            raw_msg = self.get_raw_message(event)
            if not raw_msg:
                return images
            
            # 提取当前消息中的图片
            images.extend(self._extract_images_from_message(raw_msg, "user"))
            
            # 提取引用/回复消息中的图片
            images.extend(self._extract_reply_images(raw_msg))
            
            logger.debug(f"从消息中提取到 {len(images)} 张图片")
            return images
        
        except Exception as e:
            logger.error(f"提取图片信息失败: {e}")
            return images
    
    def _extract_images_from_message(
        self, 
        raw_msg: dict[str, Any], 
        source: str = "user"
    ) -> List["ImageInfo"]:
        """从消息段中提取图片
        
        Args:
            raw_msg: 原始消息字典
            source: 图片来源（user/forward）
        
        Returns:
            图片信息列表
        """
        from iris_memory.image.models import ImageInfo
        
        images: List[ImageInfo] = []
        
        # OneBot11 消息格式：
        # { "message": [{ "type": "image", "data": { "url": "...", "file": "..." } }] }
        # 或
        # { "message": "[CQ:image,file=...,url=...]" }
        
        message_segments = raw_msg.get("message", [])
        
        # 如果 message 是字符串（CQ码格式），跳过
        if isinstance(message_segments, str):
            logger.debug("消息为 CQ 码格式，暂不支持图片提取")
            return images
        
        # 遍历消息段
        if not isinstance(message_segments, list):
            return images
        
        for segment in message_segments:
            if not isinstance(segment, dict):
                continue
            
            # 检查是否为图片段
            if segment.get("type") == "image":
                data = segment.get("data", {})
                
                image_info = ImageInfo(
                    url=data.get("url"),
                    file_path=data.get("file"),
                    format=self._detect_image_format(data.get("url", "")),
                    size_kb=0,  # OneBot11 通常不提供大小信息
                    source=source,
                    message_id=raw_msg.get("message_id", "")
                )
                
                images.append(image_info)
        
        return images
    
    def _extract_reply_images(self, raw_msg: dict[str, Any]) -> List["ImageInfo"]:
        """提取引用/回复消息中的图片
        
        Args:
            raw_msg: 原始消息字典
        
        Returns:
            图片信息列表
        """
        from iris_memory.image.models import ImageInfo
        
        images: List[ImageInfo] = []
        
        message_segments = raw_msg.get("message", [])
        
        if not isinstance(message_segments, list):
            return images
        
        for segment in message_segments:
            if not isinstance(segment, dict):
                continue
            
            # 检查是否为回复段
            if segment.get("type") == "reply":
                # 回复消息可能包含原始消息内容
                # 格式因实现而异，这里尝试提取
                data = segment.get("data", {})
                
                # 某些实现会在 data 中包含原始消息段
                if "content" in data:
                    # content 可能是消息段数组
                    content = data["content"]
                    if isinstance(content, list):
                        images.extend(self._extract_images_from_message(
                            {"message": content}, 
                            "forward"
                        ))
                
                # 某些实现会直接包含图片信息
                # 这里做兜底处理
                break
        
        return images
    
    def _detect_image_format(self, url: str) -> str:
        """检测图片格式
        
        从 URL 或文件名推断图片格式。
        
        Args:
            url: 图片 URL 或文件路径
        
        Returns:
            图片格式（jpg/jpeg/png/gif/webp）
        """
        if not url:
            return ""
        
        # 转小写
        url_lower = url.lower()
        
        # 检查常见格式
        if ".jpg" in url_lower or ".jpeg" in url_lower:
            return "jpg"
        elif ".png" in url_lower:
            return "png"
        elif ".gif" in url_lower:
            return "gif"
        elif ".webp" in url_lower:
            return "webp"
        
        # 默认返回空
        return ""
