"""
Iris Tier Memory - 图片解析数据模型

定义图片解析相关的数据结构，包括图片信息、解析结果和配额状态。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


# ============================================================================
# 图片信息
# ============================================================================

@dataclass
class ImageInfo:
    """图片信息数据类
    
    存储单张图片的完整信息，包括URL、文件路径、格式和大小。
    
    Attributes:
        url: 图片URL（网络图片）
        file_path: 图片本地文件路径（本地图片）
        format: 图片格式（jpg/jpeg/png/gif/webp）
        size_kb: 图片大小（KB）
        source: 图片来源（user/upload/forward）
        message_id: 关联的消息ID
        
    Examples:
        >>> info = ImageInfo(
        ...     url="https://example.com/image.jpg",
        ...     format="jpg",
        ...     size_kb=256
        ... )
        >>> info.format
        'jpg'
    """
    
    url: Optional[str] = None
    file_path: Optional[str] = None
    format: str = ""
    size_kb: int = 0
    source: str = "user"  # user/upload/forward
    message_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "url": self.url,
            "file_path": self.file_path,
            "format": self.format,
            "size_kb": self.size_kb,
            "source": self.source,
            "message_id": self.message_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageInfo":
        """从字典创建实例
        
        Args:
            data: 包含图片信息的字典
        
        Returns:
            ImageInfo 实例
        """
        return cls(
            url=data.get("url"),
            file_path=data.get("file_path"),
            format=data.get("format", ""),
            size_kb=data.get("size_kb", 0),
            source=data.get("source", "user"),
            message_id=data.get("message_id", ""),
        )
    
    @property
    def has_url(self) -> bool:
        """是否有URL
        
        Returns:
            是否有URL
        """
        return self.url is not None and len(self.url) > 0
    
    @property
    def has_file_path(self) -> bool:
        """是否有文件路径
        
        Returns:
            是否有文件路径
        """
        return self.file_path is not None and len(self.file_path) > 0


# ============================================================================
# 解析结果
# ============================================================================

@dataclass
class ParseResult:
    """图片解析结果数据类
    
    存储单张图片的解析结果，包括解析后的文本内容、Token数和时间戳。
    
    Attributes:
        image_info: 图片信息
        content: 解析后的文本描述
        input_tokens: 输入Token数
        output_tokens: 输出Token数
        timestamp: 解析时间戳
        success: 是否成功
        error_message: 错误信息（失败时）
        
    Examples:
        >>> result = ParseResult(
        ...     content="这是一张风景图片，显示蓝天白云",
        ...     input_tokens=150,
        ...     output_tokens=30,
        ...     success=True
        ... )
        >>> result.success
        True
    """
    
    image_info: Optional[ImageInfo] = None
    content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "image_info": self.image_info.to_dict() if self.image_info else None,
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParseResult":
        """从字典创建实例
        
        Args:
            data: 包含解析结果的字典
        
        Returns:
            ParseResult 实例
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()
        
        image_info = None
        if data.get("image_info"):
            image_info = ImageInfo.from_dict(data["image_info"])
        
        return cls(
            image_info=image_info,
            content=data.get("content", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            timestamp=timestamp,
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
        )
    
    @property
    def total_tokens(self) -> int:
        """获取总Token数
        
        Returns:
            总Token数
        """
        return self.input_tokens + self.output_tokens


# ============================================================================
# 配额状态
# ============================================================================

@dataclass
class QuotaStatus:
    """图片解析配额状态数据类
    
    存储全局图片解析配额的使用情况。
    
    Attributes:
        date: 当前日期（YYYY-MM-DD）
        used: 已使用次数
        total: 总配额
        last_reset_time: 上次重置时间
        
    Examples:
        >>> status = QuotaStatus(
        ...     date="2026-03-29",
        ...     used=15,
        ...     total=200
        ... )
        >>> status.remaining
        185
    """
    
    date: str = ""
    used: int = 0
    total: int = 200
    last_reset_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "date": self.date,
            "used": self.used,
            "total": self.total,
            "last_reset_time": self.last_reset_time.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuotaStatus":
        """从字典创建实例
        
        Args:
            data: 包含配额状态的字典
        
        Returns:
            QuotaStatus 实例
        """
        last_reset_time = data.get("last_reset_time")
        if isinstance(last_reset_time, str):
            last_reset_time = datetime.fromisoformat(last_reset_time)
        else:
            last_reset_time = datetime.now()
        
        return cls(
            date=data.get("date", ""),
            used=data.get("used", 0),
            total=data.get("total", 200),
            last_reset_time=last_reset_time,
        )
    
    @property
    def remaining(self) -> int:
        """获取剩余配额
        
        Returns:
            剩余配额
        """
        return max(0, self.total - self.used)
    
    @property
    def is_exhausted(self) -> bool:
        """配额是否已耗尽
        
        Returns:
            是否已耗尽
        """
        return self.used >= self.total


# ============================================================================
# 消息图片集合
# ============================================================================

@dataclass
class MessageImages:
    """消息图片集合数据类
    
    存储单条消息中的所有图片信息，包括当前消息的图片和引用消息的图片。
    
    Attributes:
        message_id: 消息ID
        current_images: 当前消息中的图片列表
        reply_images: 引用/回复消息中的图片列表
        is_llm_trigger: 是否触发LLM调用
        contains_keywords: 是否包含关键词
        
    Examples:
        >>> images = MessageImages(message_id="msg_123")
        >>> images.current_images.append(ImageInfo(url="https://example.com/1.jpg"))
        >>> len(images.current_images)
        1
    """
    
    message_id: str = ""
    current_images: List[ImageInfo] = field(default_factory=list)
    reply_images: List[ImageInfo] = field(default_factory=list)
    is_llm_trigger: bool = False
    contains_keywords: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "message_id": self.message_id,
            "current_images": [img.to_dict() for img in self.current_images],
            "reply_images": [img.to_dict() for img in self.reply_images],
            "is_llm_trigger": self.is_llm_trigger,
            "contains_keywords": self.contains_keywords,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageImages":
        """从字典创建实例
        
        Args:
            data: 包含消息图片的字典
        
        Returns:
            MessageImages 实例
        """
        current_images = [
            ImageInfo.from_dict(img) 
            for img in data.get("current_images", [])
        ]
        reply_images = [
            ImageInfo.from_dict(img) 
            for img in data.get("reply_images", [])
        ]
        
        return cls(
            message_id=data.get("message_id", ""),
            current_images=current_images,
            reply_images=reply_images,
            is_llm_trigger=data.get("is_llm_trigger", False),
            contains_keywords=data.get("contains_keywords", False),
        )
    
    @property
    def all_images(self) -> List[ImageInfo]:
        """获取所有图片（当前+引用）
        
        Returns:
            所有图片列表
        """
        return self.current_images + self.reply_images
    
    @property
    def has_images(self) -> bool:
        """是否有图片
        
        Returns:
            是否有图片
        """
        return len(self.current_images) > 0 or len(self.reply_images) > 0
    
    @property
    def total_count(self) -> int:
        """获取图片总数
        
        Returns:
            图片总数
        """
        return len(self.current_images) + len(self.reply_images)
